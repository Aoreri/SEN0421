"""Proje, sürüm ve gereksinim CRUD uçları + test vakası izlenebilirliği (PLN-06)."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import ADMIN, TEST_LEAD, TESTER, require_roles
from .db import DB
from .models import Project, Release, Requirement, TestCase

router = APIRouter(prefix="/api", tags=["projects"])
WRITE = [Depends(require_roles(ADMIN, TEST_LEAD))]
TRACE = [Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]


Title = StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
Short = StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
Version = StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
Code = StringConstraints(strip_whitespace=True, min_length=1, max_length=20)
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class ProjectIn(BaseModel):
    name: Annotated[str, Short]
    description: Description = ""


class ReleaseIn(BaseModel):
    project_id: int
    version: Annotated[str, Version]


class RequirementIn(BaseModel):
    project_id: int
    title: Annotated[str, Title]
    description: Description = ""


class RequirementCreate(RequirementIn):
    id: Annotated[str, Code]


class TraceLinks(BaseModel):
    test_cases: list[str]


def get_or_404[T](db: Session, model: type[T], key: Any) -> T:
    row = db.get(model, key)
    if row is None:
        raise HTTPException(404, f"{model.__name__} bulunamadı")
    return row


def commit_or_409(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Kayıt başka verilerle çakışıyor") from None


def save[T](db: Session, row: T, body: BaseModel) -> T:
    for field, value in body:
        setattr(row, field, value)
    db.add(row)
    commit_or_409(db)
    return row


def remove(db: Session, row: Any) -> None:
    db.delete(row)
    commit_or_409(db)


def require_project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(422, "Proje bulunamadı")


def project_out(p: Project) -> dict:
    return {"id": p.id, "name": p.name, "description": p.description}


def release_out(r: Release) -> dict:
    return {"id": r.id, "project_id": r.project_id, "version": r.version}


def requirement_out(r: Requirement) -> dict:
    return {"id": r.id, "project_id": r.project_id, "title": r.title, "description": r.description,
            "test_cases": sorted(t.id for t in r.test_cases)}


# --- Projeler -----------------------------------------------------------------
@router.get("/projects")
def list_projects(db: DB):
    return [project_out(p) for p in db.scalars(select(Project).order_by(Project.id))]


@router.post("/projects", status_code=201, dependencies=WRITE)
def create_project(body: ProjectIn, db: DB):
    return project_out(save(db, Project(), body))


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: DB):
    return project_out(get_or_404(db, Project, project_id))


@router.put("/projects/{project_id}", dependencies=WRITE)
def update_project(project_id: int, body: ProjectIn, db: DB):
    return project_out(save(db, get_or_404(db, Project, project_id), body))


@router.delete("/projects/{project_id}", status_code=204, dependencies=WRITE)
def delete_project(project_id: int, db: DB):
    project = get_or_404(db, Project, project_id)
    for model in (Release, Requirement):
        if db.scalar(select(model.id).where(model.project_id == project_id).limit(1)) is not None:
            raise HTTPException(409, "Projeye bağlı sürüm veya gereksinimler var")
    remove(db, project)


# --- Sürümler -----------------------------------------------------------------
@router.get("/releases")
def list_releases(db: DB):
    return [release_out(r) for r in db.scalars(select(Release).order_by(Release.id))]


@router.post("/releases", status_code=201, dependencies=WRITE)
def create_release(body: ReleaseIn, db: DB):
    require_project(db, body.project_id)
    return release_out(save(db, Release(), body))


@router.get("/releases/{release_id}")
def get_release(release_id: int, db: DB):
    return release_out(get_or_404(db, Release, release_id))


@router.put("/releases/{release_id}", dependencies=WRITE)
def update_release(release_id: int, body: ReleaseIn, db: DB):
    release = get_or_404(db, Release, release_id)
    require_project(db, body.project_id)
    return release_out(save(db, release, body))


@router.delete("/releases/{release_id}", status_code=204, dependencies=WRITE)
def delete_release(release_id: int, db: DB):
    remove(db, get_or_404(db, Release, release_id))


# --- Gereksinimler ------------------------------------------------------------
@router.get("/requirements")
def list_requirements(db: DB):
    rows = db.scalars(select(Requirement).options(selectinload(Requirement.test_cases))
                      .order_by(Requirement.id))
    return [requirement_out(r) for r in rows]


@router.post("/requirements", status_code=201, dependencies=WRITE)
def create_requirement(body: RequirementCreate, db: DB):
    require_project(db, body.project_id)
    return requirement_out(save(db, Requirement(), body))


@router.get("/requirements/{requirement_id}")
def get_requirement(requirement_id: str, db: DB):
    return requirement_out(get_or_404(db, Requirement, requirement_id))


@router.put("/requirements/{requirement_id}", dependencies=WRITE)
def update_requirement(requirement_id: str, body: RequirementIn, db: DB):
    requirement = get_or_404(db, Requirement, requirement_id)
    require_project(db, body.project_id)
    return requirement_out(save(db, requirement, body))


@router.delete("/requirements/{requirement_id}", status_code=204, dependencies=WRITE)
def delete_requirement(requirement_id: str, db: DB):
    requirement = get_or_404(db, Requirement, requirement_id)
    if requirement.test_cases:
        raise HTTPException(409, "Gereksinime bağlı test vakaları var")
    remove(db, requirement)


@router.put("/requirements/{requirement_id}/test-cases", dependencies=TRACE)
def set_requirement_test_cases(requirement_id: str, body: TraceLinks, db: DB):
    """Gereksinimin test vakası bağlantılarını verilen listeyle değiştirir (boş liste: tümünü kaldırır)."""
    requirement = get_or_404(db, Requirement, requirement_id)
    ids = set(body.test_cases)
    test_cases = list(db.scalars(select(TestCase).where(TestCase.id.in_(ids))))
    if len(test_cases) != len(ids):
        raise HTTPException(422, "Test vakası bulunamadı")
    requirement.test_cases = test_cases
    commit_or_409(db)
    return requirement_out(requirement)
