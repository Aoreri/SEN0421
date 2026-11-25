"""Sprint varlığı (sprints) ve test koşumu sprint bağlantısı (PLN-28)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-21
"""
import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True
        ),
        sa.Column(
            "release_id", sa.Integer, sa.ForeignKey("releases.id"), nullable=True, index=True
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("goal", sa.String(1000), nullable=False, server_default=""),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Planned"),
        sa.UniqueConstraint("project_id", "name"),
    )
    with op.batch_alter_table("test_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "sprint_id",
                sa.Integer,
                sa.ForeignKey("sprints.id", name="fk_test_runs_sprint_id_sprints"),
                nullable=True,
            )
        )
        batch_op.create_index("ix_test_runs_sprint_id", ["sprint_id"])


def downgrade() -> None:
    with op.batch_alter_table("test_runs") as batch_op:
        batch_op.drop_index("ix_test_runs_sprint_id")
        batch_op.drop_column("sprint_id")
    op.drop_table("sprints")
