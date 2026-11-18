"""PLN-23: authenticated Cobertura imports and retained evidence."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from .auth import CurrentUser
from .cobertura import MAX_COVERAGE_BYTES, parse_cobertura
from .db import DB
from .junit_imports import Branch, Commit, Importer
from .models import CoverageImport, ImportedTestRun, Project
from .projects import commit_or_409, get_or_404

router = APIRouter(prefix="/api/projects/{project_id}/coverage", tags=["Coverage imports"])


def report_out(report: CoverageImport, include_files: bool = True) -> dict:
    result: dict = {"id": report.id, "project_id": report.project_id,
              "imported_by": report.imported_by, "junit_import_id": report.junit_import_id,
              "commit": report.commit_sha, "branch": report.branch,
              "created_at": report.created_at, "summary": report.summary}
    if include_files:
        result["files"] = report.files
    return result


@router.post("/import", status_code=201, openapi_extra={"requestBody": {
    "required": True, "content": {"application/xml": {"schema": {"type": "string"}}},
}})
async def import_coverage(project_id: int, request: Request, db: DB, user: Importer,
                          commit: Commit = None, branch: Branch = None,
                          junit_import_id: Annotated[int | None, Query(ge=1)] = None):
    get_or_404(db, Project, project_id)
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() not in (
        "application/xml", "text/xml",
    ):
        raise HTTPException(415, "Use Content-Type: application/xml")
    if branch is not None:
        if any(ord(c) < 32 or ord(c) == 127 for c in branch):
            raise HTTPException(422, "Invalid branch metadata")
        branch = branch.strip()
    if junit_import_id is not None:
        run = get_or_404(db, ImportedTestRun, junit_import_id)
        if run.project_id != project_id:
            raise HTTPException(422, "JUnit import belongs to another project")
        if ((commit is not None and run.commit_sha != commit)
                or (branch is not None and run.branch != branch)):
            raise HTTPException(422, "Coverage metadata must match the linked JUnit import")
        commit, branch = run.commit_sha, run.branch
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_COVERAGE_BYTES:
            raise HTTPException(413, "Cobertura XML exceeds 4 MiB")
        data.extend(chunk)
    try:
        parsed = parse_cobertura(bytes(data))
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    report = CoverageImport(project_id=project_id, imported_by=user.id,
                            junit_import_id=junit_import_id, commit_sha=commit, branch=branch,
                            summary=parsed["summary"], files=parsed["files"])
    db.add(report)
    commit_or_409(db)
    return report_out(report)


@router.get("/imports")
def list_coverage(project_id: int, db: DB, user: CurrentUser,
                  limit: Annotated[int, Query(ge=1, le=100)] = 50,
                  offset: Annotated[int, Query(ge=0)] = 0):
    get_or_404(db, Project, project_id)
    return [report_out(report, False) for report in db.scalars(select(CoverageImport)
            .where(CoverageImport.project_id == project_id).order_by(CoverageImport.id.desc())
            .offset(offset).limit(limit))]


@router.get("/imports/{import_id}")
def get_coverage(project_id: int, import_id: int, db: DB, user: CurrentUser):
    report = get_or_404(db, CoverageImport, import_id)
    if report.project_id != project_id:
        raise HTTPException(404, "Coverage import not found in this project")
    return report_out(report)
