"""PLN-23: project-scoped Cobertura evidence snapshots."""
import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coverage_imports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("imported_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("junit_import_id", sa.Integer, sa.ForeignKey("imported_test_runs.id")),
        sa.Column("commit_sha", sa.String(64)),
        sa.Column("branch", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("summary", sa.JSON, nullable=False),
        sa.Column("files", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("coverage_imports")
