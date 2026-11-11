from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    requirement: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="Not Run")


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="Open")
    test_case: Mapped[str | None] = mapped_column(ForeignKey("test_cases.id"))


class DefectHistory(Base):
    """Değiştirilemez geçmiş: yalnızca INSERT. PostgreSQL'de trigger UPDATE/DELETE'i engeller."""

    __tablename__ = "defect_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
