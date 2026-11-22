"""IEEE 829 Test Incident Report ve Test Log anlık görüntü (snapshot) tabloları (PLN-39)

Revision ID: 0011_pln39
Revises: 0010
Create Date: 2026-11-22
"""
import sqlalchemy as sa

from alembic import op

revision = "0011_pln39"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_incident_report_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "defect_id", sa.Integer, sa.ForeignKey("defects.id"), nullable=False, index=True
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
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
    op.create_table(
        "test_log_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "test_run_id", sa.Integer, sa.ForeignKey("test_runs.id"), nullable=False, index=True
        ),
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
    op.drop_table("test_log_snapshots")
    op.drop_table("test_incident_report_snapshots")
