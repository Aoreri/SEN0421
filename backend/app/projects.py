"""Proje, sürüm, sprint, gereksinim, test suite ve test vakası CRUD uçları, izlenebilirlik ve sürüm çıkış kapısı (PLN-06, PLN-16, PLN-18, PLN-28)."""
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import ADMIN, TEST_LEAD, TESTER, current_user, require_roles
from .db import DB
from .models import (
    CoverageImport,
    Defect,
    ImportedTestRun,
    Project,
    Release,
    Requirement,
    Sprint,
    TestCase,
    TestExecution,
    TestPlan,
    TestRun,
    TestSuite,
    User,
    execution_defects,
)

router = APIRouter(prefix="/api", tags=["projects"])
READ = [Depends(current_user)]
WRITE = [Depends(require_roles(ADMIN, TEST_LEAD))]
TRACE = [Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]
GateManager = Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD))]

ReleaseStatus = Literal["Planned", "In Test", "Ready", "Released"]
SprintStatus = Literal["Planned", "Active", "Completed"]


Title = StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
Short = StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
Version = StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
Code = StringConstraints(strip_whitespace=True, min_length=1, max_length=20)
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Step = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Priority = Literal["Low", "Medium", "High", "Critical"]
CaseStatus = Literal["Not Run", "Passed", "Failed", "Blocked", "Skipped"]


class ProjectIn(BaseModel):
    name: Annotated[str, Short]
    description: Description = ""


class ReleaseIn(BaseModel):
    project_id: int
    version: Annotated[str, Version]


class ExitCriteriaIn(BaseModel):
    min_pass_rate: float = Field(ge=0, le=100)
    max_open_critical: int = Field(ge=0)
    min_req_coverage: float = Field(ge=0, le=100)


class ReleaseWaiverIn(BaseModel):
    reason: Reason


class ReleaseStatusIn(BaseModel):
    status: ReleaseStatus


class SprintIn(BaseModel):
    project_id: int
    release_id: int | None = None
    name: Annotated[str, Short]
    goal: Description = ""
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: SprintStatus = "Planned"


class RequirementIn(BaseModel):
    project_id: int
    title: Annotated[str, Title]
    description: Description = ""


class RequirementCreate(RequirementIn):
    id: Annotated[str, Code]


class TraceLinks(BaseModel):
    test_cases: list[str]


class RequirementLinks(BaseModel):
    requirements: list[str] = Field(min_length=1)


class TestSuiteIn(BaseModel):
    project_id: int
    name: Annotated[str, Short]
    description: Description = ""


class TestCaseIn(BaseModel):
    title: Annotated[str, Title]
    suite_id: int | None = None
    priority: Priority = "Medium"
    automated: bool = False
    steps: list[Step] = Field(default_factory=list, max_length=100)
    expected_result: Description = ""
    status: CaseStatus = "Not Run"
    requirements: list[Annotated[str, Code]] = Field(min_length=1)


class TestCaseCreate(TestCaseIn):
    id: Annotated[str, Code]


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
    return {"id": r.id, "project_id": r.project_id, "version": r.version, "status": r.status}


def normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(422, "Sprint tarihleri zaman dilimi (timezone) içermelidir")
    return value.astimezone(UTC)


def format_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def sprint_out(s: Sprint) -> dict:
    return {
        "id": s.id,
        "project_id": s.project_id,
        "release_id": s.release_id,
        "name": s.name,
        "goal": s.goal,
        "start_at": format_utc(s.start_at),
        "end_at": format_utc(s.end_at),
        "status": s.status,
    }


def validate_sprint(db: Session, body: SprintIn) -> tuple[datetime | None, datetime | None]:
    require_project(db, body.project_id)
    if body.release_id is not None:
        release = db.get(Release, body.release_id)
        if release is None or release.project_id != body.project_id:
            raise HTTPException(422, "Sürüm bulunamadı veya projeye ait değil")
    start = normalize_utc(body.start_at)
    end = normalize_utc(body.end_at)
    if start is not None and end is not None and start >= end:
        raise HTTPException(422, "start_at değeri end_at değerinden önce olmalıdır")
    return start, end


def release_gate_out(db: Session, r: Release) -> dict:
    project_case_filter = or_(
        TestCase.requirements.any(Requirement.project_id == r.project_id),
        TestCase.suite.has(TestSuite.project_id == r.project_id),
    )
    other_project_case_ids = select(TestCase.id).where(
        ~project_case_filter,
        or_(
            TestCase.requirements.any(Requirement.project_id != r.project_id),
            TestCase.suite.has(TestSuite.project_id != r.project_id),
        ),
    )
    other_project_exec_defect_ids = (
        select(execution_defects.c.defect_id)
        .join(TestExecution, TestExecution.id == execution_defects.c.execution_id)
        .join(TestRun, TestRun.id == TestExecution.run_id)
        .where(TestRun.project_id != r.project_id)
    )
    project_exec_defect_ids = (
        select(execution_defects.c.defect_id)
        .join(TestExecution, TestExecution.id == execution_defects.c.execution_id)
        .join(TestRun, TestRun.id == TestExecution.run_id)
        .where(TestRun.project_id == r.project_id)
    )

    statuses = list(db.scalars(select(TestCase.status).where(project_case_filter)))
    executed = sum(s in ("Passed", "Failed") for s in statuses)
    passed = statuses.count("Passed")
    actual_pass_rate = round(passed / executed * 100, 1) if executed else 0.0

    actual_open_critical = int(
        db.scalar(
            select(func.count()).where(
                Defect.severity == "Critical",
                Defect.status != "Closed",
                or_(
                    Defect.test_case.in_(select(TestCase.id).where(project_case_filter)),
                    Defect.id.in_(project_exec_defect_ids),
                    (
                        Defect.test_case.is_(None)
                        & ~Defect.id.in_(other_project_exec_defect_ids)
                    ),
                ),
                or_(Defect.test_case.is_(None), ~Defect.test_case.in_(other_project_case_ids)),
            )
        )
        or 0
    )

    reqs = list(
        db.scalars(
            select(Requirement)
            .where(Requirement.project_id == r.project_id)
            .options(selectinload(Requirement.test_cases))
        )
    )
    covered_reqs = sum(1 for req in reqs if req.test_cases)
    actual_req_coverage = round(covered_reqs / len(reqs) * 100, 1) if reqs else 0.0

    pass_rate_ok = actual_pass_rate >= r.min_pass_rate
    open_critical_ok = actual_open_critical <= r.max_open_critical
    req_coverage_ok = actual_req_coverage >= r.min_req_coverage

    waiver = (
        {"waived_by": r.waived_by, "reason": r.waiver_reason, "waived_at": r.waived_at}
        if r.waived_by and r.waiver_reason and r.waived_at
        else None
    )
    gate_passed = (pass_rate_ok and open_critical_ok and req_coverage_ok) or waiver is not None

    return {
        "release_id": r.id,
        "release_version": r.version,
        "status": r.status,
        "criteria": {
            "min_pass_rate": r.min_pass_rate,
            "max_open_critical": r.max_open_critical,
            "min_req_coverage": r.min_req_coverage,
        },
        "actual_pass_rate": actual_pass_rate,
        "actual_open_critical": actual_open_critical,
        "actual_req_coverage": actual_req_coverage,
        "passed_criteria": {
            "pass_rate": pass_rate_ok,
            "open_critical": open_critical_ok,
            "req_coverage": req_coverage_ok,
        },
        "gate_passed": gate_passed,
        "waiver": waiver,
    }


def requirement_out(r: Requirement) -> dict:
    return {"id": r.id, "project_id": r.project_id, "title": r.title, "description": r.description,
            "test_cases": sorted(t.id for t in r.test_cases)}


def suite_out(s: TestSuite) -> dict:
    return {"id": s.id, "project_id": s.project_id, "name": s.name, "description": s.description,
            "test_cases": sorted(t.id for t in s.test_cases)}


def test_case_out(t: TestCase) -> dict:
    return {
        "id": t.id,
        "suite_id": t.suite_id,
        "title": t.title,
        "requirement": t.requirement,
        "requirements": sorted(r.id for r in t.requirements),
        "status": t.status,
        "priority": t.priority,
        "automated": t.automated,
        "steps": t.steps,
        "expected_result": t.expected_result,
    }


def resolve_case_relations(
    db: Session, suite_id: int | None, req_ids: list[str]
) -> tuple[TestSuite | None, list[Requirement]]:
    suite = None
    if suite_id is not None:
        suite = db.get(TestSuite, suite_id)
        if suite is None:
            raise HTTPException(422, "Test suite bulunamadı")
    ids = set(req_ids)
    requirements = list(db.scalars(select(Requirement).where(Requirement.id.in_(ids))))
    if len(requirements) != len(ids):
        raise HTTPException(422, "Gereksinim bulunamadı")
    if suite is not None and any(r.project_id != suite.project_id for r in requirements):
        raise HTTPException(422, "Test suite ve gereksinimler aynı projede olmalıdır")
    return suite, requirements


# --- Projeler -----------------------------------------------------------------
@router.get("/projects", dependencies=READ)
def list_projects(db: DB):
    return [project_out(p) for p in db.scalars(select(Project).order_by(Project.id))]


@router.post("/projects", status_code=201, dependencies=WRITE)
def create_project(body: ProjectIn, db: DB):
    return project_out(save(db, Project(), body))


@router.get("/projects/{project_id}", dependencies=READ)
def get_project(project_id: int, db: DB):
    return project_out(get_or_404(db, Project, project_id))


@router.put("/projects/{project_id}", dependencies=WRITE)
def update_project(project_id: int, body: ProjectIn, db: DB):
    return project_out(save(db, get_or_404(db, Project, project_id), body))


@router.delete("/projects/{project_id}", status_code=204, dependencies=WRITE)
def delete_project(project_id: int, db: DB):
    project = get_or_404(db, Project, project_id)
    for model in (
        Release,
        Sprint,
        Requirement,
        TestSuite,
        TestRun,
        TestPlan,
        ImportedTestRun,
        CoverageImport,
    ):
        if db.scalar(select(model.id).where(model.project_id == project_id).limit(1)) is not None:
            raise HTTPException(
                409,
                "Projeye bağlı sürüm, sprint, gereksinim, test suite, test koşumu, test planı veya içe aktarım kayıtları var",
            )
    remove(db, project)


# --- Sürümler -----------------------------------------------------------------
@router.get("/releases", dependencies=READ)
def list_releases(db: DB):
    return [release_out(r) for r in db.scalars(select(Release).order_by(Release.id))]


@router.post("/releases", status_code=201, dependencies=WRITE)
def create_release(body: ReleaseIn, db: DB):
    require_project(db, body.project_id)
    return release_out(save(db, Release(), body))


@router.get("/releases/{release_id}", dependencies=READ)
def get_release(release_id: int, db: DB):
    return release_out(get_or_404(db, Release, release_id))


@router.put("/releases/{release_id}", dependencies=WRITE)
def update_release(release_id: int, body: ReleaseIn, db: DB):
    release = get_or_404(db, Release, release_id)
    require_project(db, body.project_id)
    if release.project_id != body.project_id:
        for model in (Sprint, TestRun, TestPlan):
            if db.scalar(select(model.id).where(model.release_id == release_id).limit(1)) is not None:
                raise HTTPException(409, "Bağlı kayıtları olan sürümün projesi değiştirilemez")
    return release_out(save(db, release, body))


@router.delete("/releases/{release_id}", status_code=204, dependencies=WRITE)
def delete_release(release_id: int, db: DB):
    release = get_or_404(db, Release, release_id)
    if db.scalar(select(Sprint.id).where(Sprint.release_id == release_id).limit(1)) is not None:
        raise HTTPException(409, "Sürüme bağlı sprint kayıtları var")
    if db.scalar(select(TestRun.id).where(TestRun.release_id == release_id).limit(1)) is not None:
        raise HTTPException(409, "Sürüme bağlı test koşumları var")
    if db.scalar(select(TestPlan.id).where(TestPlan.release_id == release_id).limit(1)) is not None:
        raise HTTPException(409, "Sürüme bağlı test planı var")
    remove(db, release)


@router.get("/releases/{release_id}/gate", dependencies=READ)
def get_release_gate(release_id: int, db: DB):
    release = get_or_404(db, Release, release_id)
    return release_gate_out(db, release)


@router.put("/releases/{release_id}/criteria", dependencies=WRITE)
def update_release_criteria(release_id: int, body: ExitCriteriaIn, db: DB):
    release = get_or_404(db, Release, release_id)
    save(db, release, body)
    return release_gate_out(db, release)


@router.post("/releases/{release_id}/waiver")
def create_release_waiver(release_id: int, body: ReleaseWaiverIn, db: DB, user: GateManager):
    release = get_or_404(db, Release, release_id)
    release.waived_by = user.username
    release.waiver_reason = body.reason
    release.waived_at = datetime.now(UTC)
    db.add(release)
    commit_or_409(db)
    return release_gate_out(db, release)


@router.delete("/releases/{release_id}/waiver", dependencies=WRITE)
def delete_release_waiver(release_id: int, db: DB):
    release = get_or_404(db, Release, release_id)
    release.waived_by = None
    release.waiver_reason = None
    release.waived_at = None
    db.add(release)
    commit_or_409(db)
    return release_gate_out(db, release)


@router.put("/releases/{release_id}/status", dependencies=WRITE)
def update_release_status(release_id: int, body: ReleaseStatusIn, db: DB):
    release = get_or_404(db, Release, release_id)
    gate = release_gate_out(db, release)
    if body.status in ("Ready", "Released") and not gate["gate_passed"]:
        raise HTTPException(
            409,
            "Çıkış kriterleri karşılanmadan veya muafiyet girilmeden Ready/Released yapılamaz",
        )
    release.status = body.status
    db.add(release)
    commit_or_409(db)
    return release_gate_out(db, release)


# --- Sprintler (PLN-28) -------------------------------------------------------
@router.get("/sprints", dependencies=READ)
def list_sprints(
    db: DB,
    project_id: Annotated[int | None, Query(ge=1)] = None,
    release_id: Annotated[int | None, Query(ge=1)] = None,
):
    stmt = select(Sprint).order_by(Sprint.id)
    if project_id is not None:
        stmt = stmt.where(Sprint.project_id == project_id)
    if release_id is not None:
        stmt = stmt.where(Sprint.release_id == release_id)
    return [sprint_out(s) for s in db.scalars(stmt)]


@router.post("/sprints", status_code=201, dependencies=WRITE)
def create_sprint(body: SprintIn, db: DB):
    start, end = validate_sprint(db, body)
    sprint = Sprint(
        project_id=body.project_id,
        release_id=body.release_id,
        name=body.name,
        goal=body.goal,
        start_at=start,
        end_at=end,
        status=body.status,
    )
    db.add(sprint)
    commit_or_409(db)
    return sprint_out(sprint)


@router.get("/sprints/{sprint_id}", dependencies=READ)
def get_sprint(sprint_id: int, db: DB):
    return sprint_out(get_or_404(db, Sprint, sprint_id))


@router.put("/sprints/{sprint_id}", dependencies=WRITE)
def update_sprint(sprint_id: int, body: SprintIn, db: DB):
    sprint = get_or_404(db, Sprint, sprint_id)
    start, end = validate_sprint(db, body)
    if (
        sprint.project_id != body.project_id
        and db.scalar(select(TestRun.id).where(TestRun.sprint_id == sprint_id).limit(1))
        is not None
    ):
        raise HTTPException(409, "Test koşumları bağlıyken sprint projesi değiştirilemez")
    sprint.project_id = body.project_id
    sprint.release_id = body.release_id
    sprint.name = body.name
    sprint.goal = body.goal
    sprint.start_at = start
    sprint.end_at = end
    sprint.status = body.status
    db.add(sprint)
    commit_or_409(db)
    return sprint_out(sprint)


@router.delete("/sprints/{sprint_id}", status_code=204, dependencies=WRITE)
def delete_sprint(sprint_id: int, db: DB):
    sprint = get_or_404(db, Sprint, sprint_id)
    if db.scalar(select(TestRun.id).where(TestRun.sprint_id == sprint_id).limit(1)) is not None:
        raise HTTPException(409, "Sprinte bağlı test koşumları var")
    remove(db, sprint)


# --- Gereksinimler ------------------------------------------------------------
@router.get("/requirements", dependencies=READ)
def list_requirements(db: DB):
    rows = db.scalars(select(Requirement).options(selectinload(Requirement.test_cases))
                      .order_by(Requirement.id))
    return [requirement_out(r) for r in rows]


@router.post("/requirements", status_code=201, dependencies=WRITE)
def create_requirement(body: RequirementCreate, db: DB):
    require_project(db, body.project_id)
    return requirement_out(save(db, Requirement(), body))


@router.get("/requirements/{requirement_id}", dependencies=READ)
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
    for tc in test_cases:
        if tc.suite is not None and tc.suite.project_id != requirement.project_id:
            raise HTTPException(422, "Test vakasının suite'i ile gereksinim aynı projede olmalıdır")
    requirement.test_cases = test_cases
    commit_or_409(db)
    return requirement_out(requirement)


# --- Test Suite'leri ----------------------------------------------------------
@router.get("/test-suites", dependencies=READ)
def list_test_suites(db: DB):
    rows = db.scalars(select(TestSuite).options(selectinload(TestSuite.test_cases))
                      .order_by(TestSuite.id))
    return [suite_out(s) for s in rows]


@router.post("/test-suites", status_code=201, dependencies=WRITE)
def create_test_suite(body: TestSuiteIn, db: DB):
    require_project(db, body.project_id)
    return suite_out(save(db, TestSuite(), body))


@router.get("/test-suites/{suite_id}", dependencies=READ)
def get_test_suite(suite_id: int, db: DB):
    return suite_out(get_or_404(db, TestSuite, suite_id))


@router.put("/test-suites/{suite_id}", dependencies=WRITE)
def update_test_suite(suite_id: int, body: TestSuiteIn, db: DB):
    suite = get_or_404(db, TestSuite, suite_id)
    require_project(db, body.project_id)
    if suite.project_id != body.project_id and suite.test_cases:
        raise HTTPException(409, "Test vakaları bağlıyken suite projesi değiştirilemez")
    return suite_out(save(db, suite, body))


@router.delete("/test-suites/{suite_id}", status_code=204, dependencies=WRITE)
def delete_test_suite(suite_id: int, db: DB):
    suite = get_or_404(db, TestSuite, suite_id)
    if suite.test_cases:
        raise HTTPException(409, "Test suite'e bağlı test vakaları var")
    if db.scalar(select(TestRun.id).where(TestRun.suite_id == suite_id).limit(1)) is not None:
        raise HTTPException(409, "Test suite'e bağlı test koşumları var")
    remove(db, suite)


# --- Test Vakaları ------------------------------------------------------------
@router.get("/test-cases", dependencies=READ)
def list_test_cases(db: DB):
    rows = db.scalars(select(TestCase).options(selectinload(TestCase.requirements))
                      .order_by(TestCase.id))
    return [test_case_out(t) for t in rows]


@router.post("/test-cases", status_code=201, dependencies=TRACE)
def create_test_case(body: TestCaseCreate, db: DB):
    _, requirements = resolve_case_relations(db, body.suite_id, body.requirements)
    reqs = sorted(r.id for r in requirements)
    case = TestCase(
        id=body.id,
        suite_id=body.suite_id,
        title=body.title,
        requirement=reqs[0],
        status=body.status,
        priority=body.priority,
        automated=body.automated,
        steps=body.steps,
        expected_result=body.expected_result,
        requirements=requirements,
    )
    db.add(case)
    commit_or_409(db)
    return test_case_out(case)


@router.get("/test-cases/{test_case_id}", dependencies=READ)
def get_test_case(test_case_id: str, db: DB):
    return test_case_out(get_or_404(db, TestCase, test_case_id))


@router.put("/test-cases/{test_case_id}", dependencies=TRACE)
def update_test_case(test_case_id: str, body: TestCaseIn, db: DB):
    case = get_or_404(db, TestCase, test_case_id)
    _, requirements = resolve_case_relations(db, body.suite_id, body.requirements)
    reqs = sorted(r.id for r in requirements)
    case.suite_id = body.suite_id
    case.title = body.title
    case.requirement = reqs[0]
    case.status = body.status
    case.priority = body.priority
    case.automated = body.automated
    case.steps = body.steps
    case.expected_result = body.expected_result
    case.requirements = requirements
    commit_or_409(db)
    return test_case_out(case)


@router.delete("/test-cases/{test_case_id}", status_code=204, dependencies=TRACE)
def delete_test_case(test_case_id: str, db: DB):
    case = get_or_404(db, TestCase, test_case_id)
    if db.scalar(select(Defect.id).where(Defect.test_case == test_case_id).limit(1)) is not None:
        raise HTTPException(409, "Test vakasına bağlı defect'ler var")
    if (
        db.scalar(
            select(TestExecution.id).where(TestExecution.test_case_id == test_case_id).limit(1)
        )
        is not None
    ):
        raise HTTPException(409, "Test vakasına bağlı test yürütmeleri var")
    case.requirements = []
    remove(db, case)


@router.put("/test-cases/{test_case_id}/requirements", dependencies=TRACE)
def set_test_case_requirements(test_case_id: str, body: RequirementLinks, db: DB):
    """Test vakasının gereksinim bağlantılarını verilen listeyle değiştirir (en az 1 gereksinim şart)."""
    case = get_or_404(db, TestCase, test_case_id)
    _, requirements = resolve_case_relations(db, case.suite_id, body.requirements)
    case.requirements = requirements
    case.requirement = sorted(r.id for r in requirements)[0]
    commit_or_409(db)
    return test_case_out(case)
