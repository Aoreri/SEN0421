"""Test suite tablosu ve test vakası spesifikasyonu alanları (PLN-16)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16
"""
import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_suites",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.UniqueConstraint("project_id", "name"),
    )
    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.add_column(sa.Column("suite_id", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("priority", sa.String(20), nullable=False, server_default="Medium"))
        batch_op.add_column(
            sa.Column("automated", sa.Boolean, nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("steps", sa.JSON, nullable=False, server_default="[]"))
        batch_op.add_column(
            sa.Column("expected_result", sa.String(1000), nullable=False, server_default="")
        )
        batch_op.create_foreign_key("fk_test_cases_suite_id", "test_suites", ["suite_id"], ["id"])
        batch_op.create_index("ix_test_cases_suite_id", ["suite_id"])


def downgrade() -> None:
    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.drop_index("ix_test_cases_suite_id")
        batch_op.drop_constraint("fk_test_cases_suite_id", type_="foreignkey")
        batch_op.drop_column("expected_result")
        batch_op.drop_column("steps")
        batch_op.drop_column("automated")
        batch_op.drop_column("priority")
        batch_op.drop_column("suite_id")
    op.drop_table("test_suites")
