"""IEEE 829 Test Plan ve anlık görüntü (snapshot) tabloları (PLN-26)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-17
"""
import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True
        ),
        sa.Column(
            "release_id", sa.Integer, sa.ForeignKey("releases.id"), nullable=True, index=True
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("scope", sa.String(2000), nullable=False, server_default=""),
        sa.Column("approach", sa.String(2000), nullable=False, server_default=""),
        sa.Column("pass_fail_criteria", sa.String(2000), nullable=False, server_default=""),
        sa.Column("environment", sa.String(2000), nullable=False, server_default=""),
        sa.Column("schedule_risks", sa.String(2000), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "version"),
    )
    op.create_table(
        "test_plan_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "test_plan_id",
            sa.Integer,
            sa.ForeignKey("test_plans.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("html_content", sa.Text, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("generated_by", sa.String(50), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("test_plan_snapshots")
    op.drop_table("test_plans")
