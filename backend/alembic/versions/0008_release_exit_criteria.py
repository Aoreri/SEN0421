"""Sürüm durumları, çıkış kriterleri ve Test Lead muafiyeti (PLN-18)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-17
"""
import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("releases") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(20), nullable=False, server_default="Planned")
        )
        batch_op.add_column(
            sa.Column("min_pass_rate", sa.Float, nullable=False, server_default="80.0")
        )
        batch_op.add_column(
            sa.Column("max_open_critical", sa.Integer, nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("min_req_coverage", sa.Float, nullable=False, server_default="80.0")
        )
        batch_op.add_column(sa.Column("waived_by", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("waiver_reason", sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("releases") as batch_op:
        batch_op.drop_column("waived_at")
        batch_op.drop_column("waiver_reason")
        batch_op.drop_column("waived_by")
        batch_op.drop_column("min_req_coverage")
        batch_op.drop_column("max_open_critical")
        batch_op.drop_column("min_pass_rate")
        batch_op.drop_column("status")
