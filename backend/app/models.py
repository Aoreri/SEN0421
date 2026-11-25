from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))


test_case_requirements = Table(
    "test_case_requirements",
    Base.metadata,
    Column("test_case_id", ForeignKey("test_cases.id"), primary_key=True),
    Column("requirement_id", ForeignKey("requirements.id"), primary_key=True),
)

execution_defects = Table(
    "execution_defects",
    Base.metadata,
    Column("execution_id", ForeignKey("test_executions.id"), primary_key=True),
    Column("defect_id", ForeignKey("defects.id"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(1000), default="")


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("project_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Planned", server_default="Planned"
    )
    min_pass_rate: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0, server_default="80.0"
    )
    max_open_critical: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    min_req_coverage: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0, server_default="80.0"
    )
    waived_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    waiver_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    waived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    release_id: Mapped[int | None] = mapped_column(ForeignKey("releases.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    goal: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Planned", server_default="Planned"
    )


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")
    test_cases: Mapped[list["TestCase"]] = relationship(
        secondary=test_case_requirements, back_populates="requirements")


class TestSuite(Base):
    __tablename__ = "test_suites"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(1000), default="")
    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="suite")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    suite_id: Mapped[int | None] = mapped_column(ForeignKey("test_suites.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    requirement: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="Not Run")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    automated: Mapped[bool] = mapped_column(Boolean, default=False)
    steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    expected_result: Mapped[str] = mapped_column(String(1000), default="")
    suite: Mapped[TestSuite | None] = relationship(back_populates="test_cases")
    requirements: Mapped[list[Requirement]] = relationship(
        secondary=test_case_requirements, back_populates="test_cases")


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="Open")
    test_case: Mapped[str | None] = mapped_column(ForeignKey("test_cases.id"))


class DefectTransition(Base):
    __tablename__ = "defect_transitions"

    from_status: Mapped[str] = mapped_column(String(20), primary_key=True)
    to_status: Mapped[str] = mapped_column(String(20), primary_key=True)
    allowed_roles: Mapped[list[str]] = mapped_column(JSON)


class DefectHistory(Base):
    """Değiştirilemez geçmiş: yalnızca INSERT. PostgreSQL'de trigger UPDATE/DELETE'i engeller."""

    __tablename__ = "defect_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportedTestRun(Base):
    """PLN-22 import snapshot, independent of future PLN-17 interactive runs."""

    __tablename__ = "imported_test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    imported_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    branch: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    summary: Mapped[dict[str, int]] = mapped_column(JSON)


class ImportedTestResult(Base):
    __tablename__ = "imported_test_results"
    __table_args__ = (UniqueConstraint("run_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("imported_test_runs.id"), index=True)
    position: Mapped[int]
    name: Mapped[str] = mapped_column(String(512))
    classname: Mapped[str] = mapped_column(String(512))
    suite: Mapped[str] = mapped_column(String(512))
    reported_key: Mapped[str] = mapped_column(String(512))
    test_case_id: Mapped[str | None] = mapped_column(ForeignKey("test_cases.id"))
    unmatched_reason: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    duration_seconds: Mapped[float | None]
    message: Mapped[str] = mapped_column(Text)
    failure_signature: Mapped[str | None] = mapped_column(String(64))
    defect_id: Mapped[int | None] = mapped_column(ForeignKey("defects.id"))


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    release_id: Mapped[int | None] = mapped_column(ForeignKey("releases.id"), index=True)
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id"), index=True)
    suite_id: Mapped[int | None] = mapped_column(ForeignKey("test_suites.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executions: Mapped[list["TestExecution"]] = relationship(
        back_populates="run", order_by="TestExecution.id"
    )


class TestExecution(Base):
    __tablename__ = "test_executions"
    __table_args__ = (UniqueConstraint("run_id", "test_case_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"), index=True)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="Not Run")
    actual_result: Mapped[str] = mapped_column(String(1000), default="")
    notes: Mapped[str] = mapped_column(String(1000), default="")
    executed_by: Mapped[str | None] = mapped_column(String(50))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run: Mapped[TestRun] = relationship(back_populates="executions")
    defects: Mapped[list[Defect]] = relationship(secondary=execution_defects, order_by="Defect.id")


class TestPlan(Base):
    __tablename__ = "test_plans"
    __table_args__ = (UniqueConstraint("project_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    release_id: Mapped[int | None] = mapped_column(ForeignKey("releases.id"), index=True)
    version: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    scope: Mapped[str] = mapped_column(String(2000), default="")
    approach: Mapped[str] = mapped_column(String(2000), default="")
    pass_fail_criteria: Mapped[str] = mapped_column(String(2000), default="")
    environment: Mapped[str] = mapped_column(String(2000), default="")
    schedule_risks: Mapped[str] = mapped_column(String(2000), default="")
    created_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    snapshots: Mapped[list["TestPlanSnapshot"]] = relationship(
        back_populates="test_plan",
        cascade="all, delete-orphan",
        order_by="TestPlanSnapshot.id",
    )


class TestPlanSnapshot(Base):
    __tablename__ = "test_plan_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_plan_id: Mapped[int] = mapped_column(ForeignKey("test_plans.id"), index=True)
    version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    html_content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_by: Mapped[str] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    test_plan: Mapped[TestPlan] = relationship(back_populates="snapshots")


class CoverageImport(Base):
    """PLN-23 Cobertura snapshot; source paths are labels, never filesystem reads."""

    __tablename__ = "coverage_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    imported_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    junit_import_id: Mapped[int | None] = mapped_column(ForeignKey("imported_test_runs.id"))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    branch: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    summary: Mapped[dict] = mapped_column(JSON)
    files: Mapped[list[dict]] = mapped_column(JSON)


class JUnitAutoDefect(Base):
    """One persistent incident per project, stable test-case ID and error signature."""

    __tablename__ = "junit_auto_defects"
    __table_args__ = (UniqueConstraint("project_id", "test_case_id", "failure_signature",
                                       name="uq_junit_auto_defect_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"))
    failure_signature: Mapped[str] = mapped_column(String(64))
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), unique=True)


class TestSummaryReportSnapshot(Base):
    """PLN-30 IEEE 829 Test Summary Report anlık görüntüsü (sürüm başına)."""

    __tablename__ = "test_summary_report_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id"), index=True)
    release_version: Mapped[str] = mapped_column(String(50))
    release_status: Mapped[str] = mapped_column(String(20))
    gate_passed: Mapped[bool] = mapped_column(Boolean)
    html_content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_by: Mapped[str] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TestIncidentReportSnapshot(Base):
    """PLN-39 IEEE 829 Test Incident Report anlık görüntüsü (defect başına)."""

    __tablename__ = "test_incident_report_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    html_content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_by: Mapped[str] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TestLogSnapshot(Base):
    """PLN-39 IEEE 829 Test Log anlık görüntüsü (test koşumu başına)."""

    __tablename__ = "test_log_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"), index=True)
    html_content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_by: Mapped[str] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
