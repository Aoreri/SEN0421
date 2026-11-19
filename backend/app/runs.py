"""Test koşumu (Test Run), test yürütme (Test Execution) ve yürütme ↔ defect uçları (PLN-17)."""
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import ADMIN, TEST_LEAD, TESTER, require_roles
from .db import DB
from .models import (
    Defect,
    DefectHistory,
    DefectTransition,
    Project,
    Release,
    TestCase,
    TestExecution,
    TestRun,
    TestSuite,
    User,
)

router = APIRouter(prefix="/api", tags=["test-runs"])
ExecuteUser = Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]

RunName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CaseCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Text1000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Severity = Literal["Low", "Medium", "High", "Critical"]
RecordableStatus = Literal["Passed", "Failed", "Blocked", "Skipped"]


class TestRunCreate(BaseModel):
    name: RunName
    project_id: int
    release_id: int | None = None
    suite_id: int | None = None
    test_case_ids: list[CaseCode] = Field(min_length=1)


class ExecutionRecord(BaseModel):
    status: RecordableStatus
    actual_result: Text1000 = ""
    notes: Text1000 = ""
    defect_ids: list[int] | None = None


class ExecutionDefectCreate(BaseModel):
    title: RunName
    severity: Severity = "Medium"


def execution_out(ex: TestExecution) -> dict:
    return {
        "id": ex.id,
        "run_id": ex.run_id,
        "test_case_id": ex.test_case_id,
        "status": ex.status,
        "actual_result": ex.actual_result,
        "notes": ex.notes,
        "executed_by": ex.executed_by,
        "executed_at": ex.executed_at,
        "defect_ids": [d.id for d in ex.defects],
    }


def run_out(run: TestRun) -> dict:
    return {
        "id": run.id,
        "name": run.name,
        "project_id": run.project_id,
        "release_id": run.release_id,
        "suite_id": run.suite_id,
        "created_by": run.created_by,
        "created_at": run.created_at,
        "executions": [execution_out(ex) for ex in run.executions],
    }


def load_run_or_404(db: Session, run_id: int) -> TestRun:
    stmt = (
        select(TestRun)
        .where(TestRun.id == run_id)
        .options(selectinload(TestRun.executions).selectinload(TestExecution.defects))
    )
    run = db.scalar(stmt)
    if run is None:
        raise HTTPException(404, "TestRun bulunamadı")
    return run


def load_execution_or_404(db: Session, run_id: int, execution_id: int) -> TestExecution:
    stmt = (
        select(TestExecution)
        .where(TestExecution.id == execution_id, TestExecution.run_id == run_id)
        .options(selectinload(TestExecution.defects))
    )
    ex = db.scalar(stmt)
    if ex is None:
        raise HTTPException(404, "TestExecution bulunamadı")
    return ex


@router.get("/test-runs")
def list_test_runs(db: DB):
    stmt = (
        select(TestRun)
        .options(selectinload(TestRun.executions).selectinload(TestExecution.defects))
        .order_by(TestRun.id)
    )
    return [run_out(r) for r in db.scalars(stmt)]


@router.get("/test-runs/{run_id}")
def get_test_run(run_id: int, db: DB):
    return run_out(load_run_or_404(db, run_id))


@router.post("/test-runs", status_code=201)
def create_test_run(body: TestRunCreate, db: DB, user: ExecuteUser):
    if db.get(Project, body.project_id) is None:
        raise HTTPException(422, "Proje bulunamadı")
    if body.release_id is not None:
        release = db.get(Release, body.release_id)
        if release is None or release.project_id != body.project_id:
            raise HTTPException(422, "Sürüm bulunamadı veya projeye ait değil")
    if body.suite_id is not None:
        suite = db.get(TestSuite, body.suite_id)
        if suite is None or suite.project_id != body.project_id:
            raise HTTPException(422, "Test suite bulunamadı veya projeye ait değil")
    ordered_case_ids = list(dict.fromkeys(body.test_case_ids))
    found_cases = set(db.scalars(select(TestCase.id).where(TestCase.id.in_(ordered_case_ids))))
    if len(found_cases) != len(ordered_case_ids):
        raise HTTPException(422, "Test vakası bulunamadı")

    run = TestRun(
        name=body.name,
        project_id=body.project_id,
        release_id=body.release_id,
        suite_id=body.suite_id,
        created_by=user.username,
    )
    db.add(run)
    db.flush()
    for tc_id in ordered_case_ids:
        db.add(TestExecution(run_id=run.id, test_case_id=tc_id, status="Not Run"))
    db.commit()
    return run_out(load_run_or_404(db, run.id))


@router.post("/test-runs/{run_id}/executions/{execution_id}")
@router.put("/test-runs/{run_id}/executions/{execution_id}")
def record_execution(
    run_id: int, execution_id: int, body: ExecutionRecord, db: DB, user: ExecuteUser
):
    ex = load_execution_or_404(db, run_id, execution_id)
    if body.defect_ids is not None:
        unique_ids = list(dict.fromkeys(body.defect_ids))
        defects = list(
            db.scalars(select(Defect).where(Defect.id.in_(unique_ids)).order_by(Defect.id))
        )
        if len(defects) != len(unique_ids):
            raise HTTPException(422, "Defect bulunamadı")
        ex.defects = defects

    ex.status = body.status
    ex.actual_result = body.actual_result
    ex.notes = body.notes
    ex.executed_by = user.username
    ex.executed_at = datetime.now(UTC)

    tc = db.get(TestCase, ex.test_case_id)
    if tc is not None:
        tc.status = body.status

    db.commit()
    return execution_out(load_execution_or_404(db, run_id, execution_id))


@router.post("/test-runs/{run_id}/executions/{execution_id}/defects", status_code=201)
def create_defect_from_execution(
    run_id: int, execution_id: int, body: ExecutionDefectCreate, db: DB, user: ExecuteUser
):
    ex = load_execution_or_404(db, run_id, execution_id)
    defect = Defect(
        title=body.title,
        severity=body.severity,
        status="Open",
        test_case=ex.test_case_id,
    )
    db.add(defect)
    db.flush()
    db.add(DefectHistory(defect_id=defect.id, from_status=None, to_status="Open"))
    ex.defects.append(defect)
    db.commit()

    rules = list(db.scalars(select(DefectTransition).order_by(DefectTransition.to_status)))
    allowed = [
        r.to_status
        for r in rules
        if r.from_status == defect.status and user.role in r.allowed_roles
    ]
    return {
        "id": defect.id,
        "title": defect.title,
        "severity": defect.severity,
        "status": defect.status,
        "test_case": defect.test_case,
        "allowed": allowed,
    }
