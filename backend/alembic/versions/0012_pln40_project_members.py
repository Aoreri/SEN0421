"""Proje üyeliği: Tester ve Developer için proje bazlı erişim (PLN-40)

Revision ID: 0012_pln40
Revises: 0011_pln39
Create Date: 2026-11-25
"""
import sqlalchemy as sa

from alembic import op

revision = "0012_pln40"
down_revision = "0011_pln39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_members",
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True, index=True),
    )
    # Mevcut Tester ve Developer hesapları bugünkü erişimlerini kaybetmesin: tüm projelere üye yapılır.
    op.execute(
        "INSERT INTO project_members (project_id, user_id) "
        "SELECT p.id, u.id FROM projects p CROSS JOIN users u "
        "WHERE u.role IN ('Tester', 'Developer')"
    )


def downgrade() -> None:
    op.drop_table("project_members")
