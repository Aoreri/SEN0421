"""Proje üyeliği ve proje bazlı erişim (PLN-40).

Admin ve Test Lead tüm projeleri görür ve üyeleri yönetir. Tester ve Developer yalnızca üye
oldukları projelerin kayıtlarını görür ve değiştirir. Hiçbir projeye bağlı olmayan kayıt
(ör. test vakası seçilmeden açılmış defect) herkese görünür.
"""
from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from .auth import ADMIN, TEST_LEAD, CurrentUser, require_roles, user_out
from .db import DB
from .models import (
    Defect,
    Project,
    TestCase,
    TestExecution,
    TestRun,
    User,
    execution_defects,
    project_members,
)

GLOBAL_ROLES = (ADMIN, TEST_LEAD)
router = APIRouter(prefix="/api", tags=["project-members"])
Manager = Annotated[User, Depends(require_roles(*GLOBAL_ROLES))]


def allowed_projects(db: Session, user: User) -> set[int] | None:
    """Kullanıcının görebildiği proje id'leri; None tüm projeler demektir."""
    if user.role in GLOBAL_ROLES:
        return None
    return set(db.scalars(
        select(project_members.c.project_id).where(project_members.c.user_id == user.id)))


def visible(allowed: set[int] | None, project_ids: Iterable[int]) -> bool:
    ids = set(project_ids)
    return allowed is None or not ids or bool(ids & allowed)


def require_access(db: Session, user: User, project_ids: Iterable[int]) -> None:
    # 404: üye olmayan kullanıcı başka projedeki kaydın varlığını öğrenmesin.
    if not visible(allowed_projects(db, user), project_ids):
        raise HTTPException(404, "Kayıt bulunamadı")


def scoped[S: Select](stmt: S, column, allowed: set[int] | None) -> S:
    return stmt if allowed is None else stmt.where(column.in_(allowed))


def case_projects(tc: TestCase) -> set[int]:
    ids = {r.project_id for r in tc.requirements}
    if tc.suite is not None:
        ids.add(tc.suite.project_id)
    return ids


def defect_projects(db: Session, defect: Defect) -> set[int]:
    ids = set(db.scalars(
        select(TestRun.project_id)
        .join(TestExecution, TestExecution.run_id == TestRun.id)
        .join(execution_defects, execution_defects.c.execution_id == TestExecution.id)
        .where(execution_defects.c.defect_id == defect.id)))
    tc = db.get(TestCase, defect.test_case) if defect.test_case else None
    return ids | case_projects(tc) if tc else ids


def case_visible(allowed: set[int] | None, tc: TestCase) -> bool:
    return allowed is None or visible(allowed, case_projects(tc))


def defect_visible(db: Session, allowed: set[int] | None, defect: Defect) -> bool:
    return allowed is None or visible(allowed, defect_projects(db, defect))


def require_defect_access(db: Session, user: User, defect: Defect) -> None:
    if user.role not in GLOBAL_ROLES:
        require_access(db, user, defect_projects(db, defect))


# --- Üye yönetimi -------------------------------------------------------------
def members_out(db: Session, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(User).join(project_members, project_members.c.user_id == User.id)
        .where(project_members.c.project_id == project_id).order_by(User.username))
    return [user_out(u) for u in rows]


def project_and_user(db: Session, project_id: int, user_id: int) -> User:
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Proje bulunamadı")
    member = db.get(User, user_id)
    if member is None:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return member


@router.get("/users")
def list_users(db: DB, _: Manager):
    return [user_out(u) for u in db.scalars(select(User).order_by(User.username))]


@router.get("/projects/{project_id}/members")
def list_members(project_id: int, db: DB, _: Manager):
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Proje bulunamadı")
    return members_out(db, project_id)


@router.put("/projects/{project_id}/members/{user_id}")
def add_member(project_id: int, user_id: int, db: DB, _: Manager):
    member = project_and_user(db, project_id, user_id)
    if member.role in GLOBAL_ROLES:
        raise HTTPException(422, "Admin ve Test Lead zaten tüm projelere erişir")
    exists = db.scalar(select(project_members.c.user_id).where(
        project_members.c.project_id == project_id, project_members.c.user_id == user_id))
    if exists is None:
        db.execute(project_members.insert().values(project_id=project_id, user_id=user_id))
        db.commit()
    return members_out(db, project_id)


@router.delete("/projects/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, db: DB, _: Manager):
    project_and_user(db, project_id, user_id)
    db.execute(delete(project_members).where(
        project_members.c.project_id == project_id, project_members.c.user_id == user_id))
    db.commit()
    return members_out(db, project_id)


def project_access(project_id: int, db: DB, user: CurrentUser) -> None:
    """Yolunda project_id olan router'lar için (JUnit ve Cobertura içe aktarımları)."""
    require_access(db, user, [project_id])
