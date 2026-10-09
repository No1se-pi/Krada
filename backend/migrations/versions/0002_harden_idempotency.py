"""Harden idempotency and persist attempt outcomes.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Existing raids predate request keys, therefore the new column is nullable. All new writes
    # populate it, while PostgreSQL's unique constraint still permits legacy NULL rows.
    op.add_column("raid_instances", sa.Column("idempotency_key", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_raid_instances_idempotency_key", "raid_instances", ["idempotency_key"]
    )
    op.create_index(
        "uq_one_active_raid_per_character",
        "raid_instances",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("state = 'ACTIVE'"),
    )

    for column in ("score_awarded", "xp_awarded", "embers_awarded"):
        op.add_column(
            "question_attempts",
            sa.Column(column, sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("question_attempts", column, server_default=None)


def downgrade():
    for column in ("embers_awarded", "xp_awarded", "score_awarded"):
        op.drop_column("question_attempts", column)
    op.drop_index("uq_one_active_raid_per_character", table_name="raid_instances")
    op.drop_constraint("uq_raid_instances_idempotency_key", "raid_instances", type_="unique")
    op.drop_column("raid_instances", "idempotency_key")
