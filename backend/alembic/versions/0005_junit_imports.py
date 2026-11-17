"""PLN-22: JUnit import snapshots and matched/unmatched results.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imported_test_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("imported_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("commit_sha", sa.String(64)),
        sa.Column("branch", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("summary", sa.JSON, nullable=False),
    )
    op.create_table(
        "imported_test_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("imported_test_runs.id"),
                  nullable=False, index=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("classname", sa.String(512), nullable=False),
        sa.Column("suite", sa.String(512), nullable=False),
        sa.Column("reported_key", sa.String(512), nullable=False),
        sa.Column("test_case_id", sa.String(20), sa.ForeignKey("test_cases.id")),
        sa.Column("unmatched_reason", sa.String(40)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duration_seconds", sa.Float),
        sa.Column("message", sa.Text, nullable=False),
        sa.UniqueConstraint("run_id", "position"),
    )


def downgrade() -> None:
    op.drop_table("imported_test_results")
    op.drop_table("imported_test_runs")
