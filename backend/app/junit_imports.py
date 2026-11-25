"""PLN-22: persist JUnit import snapshots and project-scoped mapping reports."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .access import project_access
from .auth import ADMIN, TEST_LEAD, TESTER, CurrentUser, require_roles
from .db import DB
from .junit import MAX_XML_BYTES, parse_junit
from .junit_defects import failure_defect
from .models import ImportedTestResult, ImportedTestRun, Project, Requirement, TestCase, User
from .projects import get_or_404

router = APIRouter(prefix="/api/projects/{project_id}/runs", tags=["JUnit imports"],
                   dependencies=[Depends(project_access)])
Importer = Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]
Commit = Annotated[str | None, Query(pattern=r"^[a-fA-F0-9]{7,64}$", max_length=64)]
Branch = Annotated[str | None, Query(min_length=1, max_length=255, pattern=r".*\S.*")]


def run_out(run: ImportedTestRun) -> dict:
    return {"id": run.id, "project_id": run.project_id, "imported_by": run.imported_by,
            "commit": run.commit_sha, "branch": run.branch, "created_at": run.created_at,
            "summary": run.summary}


def detail(db: Session, run: ImportedTestRun) -> dict:
    results = [{"position": r.position, "name": r.name, "classname": r.classname,
                "suite": r.suite, "reported_key": r.reported_key, "test_case_id": r.test_case_id,
                "status": r.status, "duration_seconds": r.duration_seconds, "message": r.message,
                "unmatched_reason": r.unmatched_reason, "failure_signature": r.failure_signature,
                "defect_id": r.defect_id}
               for r in db.scalars(select(ImportedTestResult)
                                   .where(ImportedTestResult.run_id == run.id)
                                   .order_by(ImportedTestResult.position))]
    return {**run_out(run), "results": results,
            "unmatched_results": [r for r in results if r["unmatched_reason"] is not None]}


@router.post("/import", status_code=201, openapi_extra={"requestBody": {
    "required": True, "content": {"application/xml": {"schema": {"type": "string"}}},
}})
async def import_junit(project_id: int, request: Request, db: DB, user: Importer,
                       commit: Commit = None, branch: Branch = None):
    get_or_404(db, Project, project_id)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower().strip()
    if content_type not in ("application/xml", "text/xml"):
        raise HTTPException(415, "JUnit XML için Content-Type: application/xml kullanın")
    if branch is not None and any(ord(c) < 32 or ord(c) == 127 for c in branch):
        raise HTTPException(422, "Geçersiz branch üst verisi")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_XML_BYTES:
            raise HTTPException(413, "JUnit XML en fazla 1 MiB olabilir")
        data.extend(chunk)
    try:
        parsed = parse_junit(bytes(data))
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    keys = {r.key for r in parsed}
    known = set(db.scalars(select(TestCase.id).where(TestCase.id.in_(keys))))
    linked = set(db.scalars(select(TestCase.id).where(
        TestCase.id.in_(keys), TestCase.requirements.any(Requirement.project_id == project_id))))
    matched_count = sum(r.key in linked for r in parsed)
    summary = {"total": len(parsed), "matched": matched_count,
               "unmatched": len(parsed) - matched_count,
               **{status.lower(): sum(r.status == status for r in parsed)
                  for status in ("Passed", "Failed", "Skipped")}}
    run = ImportedTestRun(project_id=project_id, imported_by=user.id, commit_sha=commit,
                          branch=branch.strip() if branch is not None else None, summary=summary)
    try:
        db.add(run)
        db.flush()
        for position, result in enumerate(parsed):
            matched = result.key in linked
            reason = (None if matched else "not_linked_to_project" if result.key in known
                      else "unknown_test_case")
            defect_id = (failure_defect(db, project_id, result.key, result)
                         if matched and result.status == "Failed" else None)
            db.add(ImportedTestResult(
                run_id=run.id, position=position, name=result.name, classname=result.classname,
                suite=result.suite, reported_key=result.key,
                test_case_id=result.key if matched else None, unmatched_reason=reason,
                status=result.status, duration_seconds=result.duration_seconds, message=result.message,
                failure_signature=result.failure_signature, defect_id=defect_id,
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "İçe aktarım bağlı kayıtlarla çakışıyor; hiçbir sonuç kaydedilmedi") from None
    return detail(db, run)


@router.get("/imports")
def list_imports(project_id: int, db: DB, user: CurrentUser,
                 limit: Annotated[int, Query(ge=1, le=100)] = 50,
                 offset: Annotated[int, Query(ge=0)] = 0):
    get_or_404(db, Project, project_id)
    return [run_out(run) for run in db.scalars(select(ImportedTestRun)
            .where(ImportedTestRun.project_id == project_id).order_by(ImportedTestRun.id.desc())
            .offset(offset).limit(limit))]


@router.get("/imports/{import_id}")
def get_import(project_id: int, import_id: int, db: DB, user: CurrentUser):
    run = get_or_404(db, ImportedTestRun, import_id)
    if run.project_id != project_id:
        raise HTTPException(404, "İçe aktarım bu projede bulunamadı")
    return detail(db, run)
