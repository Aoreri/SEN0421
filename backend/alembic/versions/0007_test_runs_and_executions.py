"""Test koşumu (test_runs), test yürütme (test_executions) ve defect bağlantısı (PLN-17)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17
"""
import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True
        ),
        sa.Column(
            "release_id", sa.Integer, sa.ForeignKey("releases.id"), nullable=True, index=True
        ),
        sa.Column(
            "suite_id", sa.Integer, sa.ForeignKey("test_suites.id"), nullable=True, index=True
        ),
        sa.Column("created_by", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "test_executions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "run_id", sa.Integer, sa.ForeignKey("test_runs.id"), nullable=False, index=True
        ),
        sa.Column(
            "test_case_id",
            sa.String(20),
            sa.ForeignKey("test_cases.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="Not Run"),
        sa.Column("actual_result", sa.String(1000), nullable=False, server_default=""),
        sa.Column("notes", sa.String(1000), nullable=False, server_default=""),
        sa.Column("executed_by", sa.String(50), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("run_id", "test_case_id"),
    )
    op.create_table(
        "execution_defects",
        sa.Column(
            "execution_id", sa.Integer, sa.ForeignKey("test_executions.id"), primary_key=True
        ),
        sa.Column("defect_id", sa.Integer, sa.ForeignKey("defects.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("execution_defects")
    op.drop_table("test_executions")
    op.drop_table("test_runs")
