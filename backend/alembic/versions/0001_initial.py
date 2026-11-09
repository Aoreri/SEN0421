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
    test_cases = op.create_table(
        "test_cases",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("requirement", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )
    defects = op.create_table(
        "defects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("test_case", sa.String(20), sa.ForeignKey("test_cases.id")),
    )
    history = op.create_table(
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

    # Demo'daki bellek içi tohum veri
    op.bulk_insert(test_cases, [
        {"id": "TC-001", "title": "Kullanıcı girişi başarılı", "requirement": "R1", "status": "Passed"},
        {"id": "TC-002", "title": "Hatalı şifre ile giriş reddedilir", "requirement": "R1", "status": "Passed"},
        {"id": "TC-003", "title": "Defect oluşturma formu", "requirement": "R3", "status": "Failed"},
        {"id": "TC-004", "title": "Defect durum geçişi kuralları", "requirement": "R4", "status": "Passed"},
        {"id": "TC-005", "title": "Test özet raporu üretimi", "requirement": "R6", "status": "Not Run"},
        {"id": "TC-006", "title": "JUnit sonuç içe aktarımı", "requirement": "R7", "status": "Blocked"},
    ])
    seed_defects = [
        {"id": 1, "title": "Defect formu boş başlığı kabul ediyor", "severity": "High",
         "status": "Open", "test_case": "TC-003"},
        {"id": 2, "title": "Dashboard grafiği yavaş yükleniyor", "severity": "Medium",
         "status": "In Progress", "test_case": None},
        {"id": 3, "title": "PDF raporunda Türkçe karakter sorunu", "severity": "Low",
         "status": "Resolved", "test_case": "TC-005"},
    ]
    op.bulk_insert(defects, seed_defects)
    op.bulk_insert(history, [
        {"defect_id": d["id"], "from_status": None, "to_status": d["status"]} for d in seed_defects
    ])
    if op.get_bind().dialect.name == "postgresql":
        # Elle verilen id'lerden sonra sequence'i ilerlet
        op.execute("SELECT setval('defects_id_seq', (SELECT MAX(id) FROM defects))")


def downgrade() -> None:
    op.drop_table("defect_history")
    op.drop_table("defects")
    op.drop_table("test_cases")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS defect_history_immutable()")
