"""Projeler, sürümler, gereksinimler ve test vakası izlenebilirliği (PLN-06)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09
"""
import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    projects = op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(1000), nullable=False),
    )
    op.create_table(
        "releases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.UniqueConstraint("project_id", "version"),
    )
    requirements = op.create_table(
        "requirements",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
    )
    op.create_table(
        "test_case_requirements",
        sa.Column("test_case_id", sa.String(20), sa.ForeignKey("test_cases.id"), primary_key=True),
        sa.Column("requirement_id", sa.String(20), sa.ForeignKey("requirements.id"), primary_key=True),
    )

    # Boş tabloda ilk kayıt id=1 alır; R1-R8 başlıkları yer tutucudur.
    op.bulk_insert(projects, [{"name": "SDS-06", "description": ""}])
    op.bulk_insert(requirements, [
        {"id": f"R{n}", "project_id": 1, "title": f"Gereksinim R{n}", "description": ""}
        for n in range(1, 9)
    ])
    # Mevcut test vakası -> gereksinim eşlemesini koru
    op.execute("""
        INSERT INTO test_case_requirements (test_case_id, requirement_id)
        SELECT id, requirement FROM test_cases WHERE requirement IN (SELECT id FROM requirements)
    """)


def downgrade() -> None:
    op.drop_table("test_case_requirements")
    op.drop_table("requirements")
    op.drop_table("releases")
    op.drop_table("projects")
