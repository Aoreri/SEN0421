"""Defect geçiş kuralları tablosu + yaşam döngüsü tohumu (PLN-07)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09
"""
import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

FIX = ["Developer", "Admin"]
VERIFY = ["Tester", "Test Lead", "Admin"]


def upgrade() -> None:
    transitions = op.create_table(
        "defect_transitions",
        sa.Column("from_status", sa.String(20), primary_key=True),
        sa.Column("to_status", sa.String(20), primary_key=True),
        sa.Column("allowed_roles", sa.JSON, nullable=False),
    )
    op.bulk_insert(transitions, [
        {"from_status": "Open", "to_status": "In Progress", "allowed_roles": FIX},
        {"from_status": "In Progress", "to_status": "Resolved", "allowed_roles": FIX},
        {"from_status": "Resolved", "to_status": "Closed", "allowed_roles": VERIFY},
        {"from_status": "Resolved", "to_status": "Open", "allowed_roles": VERIFY},  # Reopen
        {"from_status": "Closed", "to_status": "Open", "allowed_roles": VERIFY},  # Reopen
    ])


def downgrade() -> None:
    op.drop_table("defect_transitions")
