"""Kullanıcılar tablosu + her rol için bir demo kullanıcı (PLN-05)

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

# "demo1234" için bcrypt özeti; yalnızca demo verisi, parola README'de belgelidir.
DEMO_HASH = "$2b$12$SprgTF7gPXa1GnXin3t49.S5LO2udixOI8mEKMn/mBKaPlRbh1VnK"


def upgrade() -> None:
    users = op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
    )
    op.bulk_insert(users, [
        {"username": username, "password_hash": DEMO_HASH, "role": role}
        for username, role in [("admin", "Admin"), ("testlead", "Test Lead"),
                               ("tester", "Tester"), ("developer", "Developer")]
    ])


def downgrade() -> None:
    op.drop_table("users")
