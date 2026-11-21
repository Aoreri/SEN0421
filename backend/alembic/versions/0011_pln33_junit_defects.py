"""PLN-33: deduplicated JUnit failure incidents and import-result links."""
import sqlalchemy as sa

from alembic import op

revision = "0011_pln33"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "junit_auto_defects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("test_case_id", sa.String(20), sa.ForeignKey("test_cases.id"), nullable=False),
        sa.Column("failure_signature", sa.String(64), nullable=False),
        sa.Column("defect_id", sa.Integer, sa.ForeignKey("defects.id"), nullable=False, unique=True),
        sa.UniqueConstraint("project_id", "test_case_id", "failure_signature",
                            name="uq_junit_auto_defect_key"),
    )
    with op.batch_alter_table("imported_test_results") as batch:
        batch.add_column(sa.Column("failure_signature", sa.String(64)))
        batch.add_column(sa.Column("defect_id", sa.Integer))
        batch.create_foreign_key("fk_imported_result_defect", "defects", ["defect_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("imported_test_results") as batch:
        batch.drop_constraint("fk_imported_result_defect", type_="foreignkey")
        batch.drop_column("defect_id")
        batch.drop_column("failure_signature")
    # Keep defects and their immutable history: rollback removes only import links.
    op.drop_table("junit_auto_defects")
