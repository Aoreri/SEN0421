"""IEEE 829 Test Summary Report anlık görüntü (snapshot) tablosu (PLN-30)

Revision ID: 0011_pln30
Revises: 0011
Create Date: 2026-11-22
"""
import sqlalchemy as sa

from alembic import op

revision = "0011_pln30"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_summary_report_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "release_id", sa.Integer, sa.ForeignKey("releases.id"), nullable=False, index=True
        ),
        sa.Column("release_version", sa.String(50), nullable=False),
        sa.Column("release_status", sa.String(20), nullable=False),
        sa.Column("gate_passed", sa.Boolean, nullable=False),
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
    op.drop_table("test_summary_report_snapshots")
