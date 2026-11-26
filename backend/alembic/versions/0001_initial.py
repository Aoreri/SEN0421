"""İlk şema: test vakaları, defect'ler, değiştirilemez geçmiş + demo tohum verisi

Revision ID: 0001
Revises:
Create Date: 2026-11-06
"""
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_cases",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("requirement", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_table(
        "defects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("test_case", sa.String(20), sa.ForeignKey("test_cases.id")),
    )
    op.create_table(
        "defect_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("defect_id", sa.Integer, sa.ForeignKey("defects.id"), nullable=False, index=True),
        sa.Column("from_status", sa.String(20)),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    if op.get_bind().dialect.name == "postgresql":
        # Geçmiş tablosu değiştirilemez: UPDATE/DELETE veritabanı seviyesinde reddedilir
        op.execute("""
            CREATE FUNCTION defect_history_immutable() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'defect_history is append-only'; END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE TRIGGER defect_history_no_change BEFORE UPDATE OR DELETE ON defect_history
            FOR EACH ROW EXECUTE FUNCTION defect_history_immutable();
        """)

    # Demo verisi PLN-38 ile app/demo.py'ye taşındı; yalnızca DEMO_MODE=1 iken eklenir.

def downgrade() -> None:
    op.drop_table("defect_history")
    op.drop_table("defects")
    op.drop_table("test_cases")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS defect_history_immutable()")
