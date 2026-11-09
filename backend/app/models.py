from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Table, UniqueConstraint, func
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


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")
    test_cases: Mapped[list["TestCase"]] = relationship(
        secondary=test_case_requirements, back_populates="requirements")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    requirement: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="Not Run")
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
