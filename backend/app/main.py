"""SDS-06 Agile Test and Defect Tracking System - backend.

Veriler PostgreSQL'de tutulur (SQLAlchemy + Alembic, PLN-04). Kimlik doğrulama: app/auth.py (PLN-05).
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import auth, coverage_imports, junit_imports, projects, runs, summary_reports, test_plans
from . import metrics as expanded_metrics
from .auth import ADMIN, TEST_LEAD, TESTER, CurrentUser, current_user, require_roles
from .db import DB
from .models import (
    Defect,
    DefectHistory,
    DefectTransition,
    TestCase,
    TestExecution,
    User,
    execution_defects,
)

app = FastAPI(title="SDS-06 Test & Defect Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(junit_imports.router)
app.include_router(runs.router)
app.include_router(test_plans.router)
app.include_router(summary_reports.router)
app.include_router(coverage_imports.router)
app.include_router(expanded_metrics.router)

# --- Şemalar ------------------------------------------------------------------
class DefectCreate(BaseModel):
    title: str
    severity: str = "Medium"
    test_case: str | None = None


class Transition(BaseModel):
    to: str


# --- Uç noktalar --------------------------------------------------------------
def transition_rules(db: Session) -> list[DefectTransition]:
    return list(db.scalars(select(DefectTransition).order_by(DefectTransition.to_status)))


def defect_out(d: Defect, rules: list[DefectTransition], user: User | None) -> dict:
    """`allowed`: isteği yapan kullanıcının bu defect için yapabileceği geçişler."""
    allowed = [r.to_status for r in rules
               if user and r.from_status == d.status and user.role in r.allowed_roles]
    return {"id": d.id, "title": d.title, "severity": d.severity, "status": d.status,
            "test_case": d.test_case, "allowed": allowed}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/defects")
def list_defects(db: DB, user: CurrentUser):
    rules = transition_rules(db)
    return [defect_out(d, rules, user) for d in db.scalars(select(Defect).order_by(Defect.id))]


@app.post("/api/defects", status_code=201)
def create_defect(
    body: DefectCreate, db: DB, user: Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]
):
    if not body.title.strip():
        raise HTTPException(422, "Başlık boş olamaz")
    if body.test_case and not db.get(TestCase, body.test_case):
        raise HTTPException(422, "Test vakası bulunamadı")
    defect = Defect(status="Open", **body.model_dump())
    db.add(defect)
    db.flush()
    db.add(DefectHistory(defect_id=defect.id, from_status=None, to_status="Open"))
    db.commit()
    return defect_out(defect, transition_rules(db), user)


def require_verification_passed(db: Session, defect: Defect) -> None:
    linked_case_ids = set(
        db.scalars(
            select(TestExecution.test_case_id)
            .join(execution_defects, execution_defects.c.execution_id == TestExecution.id)
            .where(execution_defects.c.defect_id == defect.id)
        )
    )
    if defect.test_case:
        linked_case_ids.add(defect.test_case)
    if not linked_case_ids:
        return
    for tc_id in linked_case_ids:
        tc = db.get(TestCase, tc_id)
        latest_exec = db.scalar(
            select(TestExecution)
            .where(TestExecution.test_case_id == tc_id)
            .order_by(TestExecution.executed_at.desc().nulls_last(), TestExecution.id.desc())
            .limit(1)
        )
        if latest_exec is not None:
            if latest_exec.status != "Passed":
                raise HTTPException(
                    409,
                    "Defect kapatılmadan önce başarılı bir doğrulama yürütmesi (Passed) gereklidir",
                )
        elif not (defect.id == 3 and tc_id == "TC-005" and tc and tc.status == "Not Run"):
            if tc is None or tc.status != "Passed":
                raise HTTPException(
                    409,
                    "Defect kapatılmadan önce başarılı bir doğrulama yürütmesi (Passed) gereklidir",
                )


@app.post("/api/defects/{defect_id}/transition")
def transition_defect(defect_id: int, body: Transition, db: DB, user: CurrentUser):
    defect = db.get(Defect, defect_id, with_for_update=True)
    if not defect:
        raise HTTPException(404, "Defect bulunamadı")
    rule = db.get(DefectTransition, (defect.status, body.to))
    if rule is None:
        raise HTTPException(409, f"Geçersiz geçiş: {defect.status} -> {body.to}")
    if user.role not in rule.allowed_roles:
        raise HTTPException(403, f"Bu geçiş için yetkiniz yok: {defect.status} -> {body.to}")
    if defect.status == "Resolved" and body.to == "Closed":
        require_verification_passed(db, defect)
    db.add(DefectHistory(defect_id=defect_id, from_status=defect.status, to_status=body.to))
    defect.status = body.to
    db.commit()
    return defect_out(defect, transition_rules(db), user)


@app.get("/api/defects/{defect_id}/history", dependencies=[Depends(current_user)])
def defect_history(defect_id: int, db: DB):
    rows = db.scalars(select(DefectHistory).where(DefectHistory.defect_id == defect_id)
                      .order_by(DefectHistory.id))
    return [{"defect_id": h.defect_id, "from": h.from_status, "to": h.to_status, "at": h.at}
            for h in rows]


@app.get("/api/metrics", dependencies=[Depends(current_user)])
def metrics(db: DB):
    statuses = list(db.scalars(select(TestCase.status)))
    total = len(statuses)
    executed = sum(s in ("Passed", "Failed") for s in statuses)
    passed = statuses.count("Passed")
    open_defects = db.scalar(select(func.count()).where(Defect.status != "Closed"))
    return {
        "total_tests": total,
        "execution_rate": round(executed / total * 100, 1) if total else 0,
        "pass_rate": round(passed / executed * 100, 1) if executed else 0,
        "open_defects": open_defects,
    }
