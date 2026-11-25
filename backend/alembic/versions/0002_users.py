"""Kullanıcılar tablosu (PLN-05)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09
"""
import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
    )
    # Demo hesapları PLN-38 ile app/demo.py'ye taşındı; yalnızca DEMO_MODE=1 iken eklenir.

def downgrade() -> None:
    op.drop_table("users")
