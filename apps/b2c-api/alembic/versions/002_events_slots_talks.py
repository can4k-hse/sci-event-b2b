"""Add events, slots, talks, user_slot_selections

Revision ID: 002
Revises: 001
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )

    op.create_table(
        "slots",
        sa.Column("slot_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.event_id"],
            name="fk_slots_event_id", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("slot_id"),
    )
    op.create_index("ix_slots_event_id", "slots", ["event_id"])

    op.create_table(
        "talks",
        sa.Column("talk_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slot_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("speaker", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["slots.slot_id"],
            name="fk_talks_slot_id", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("talk_id"),
    )
    op.create_index("ix_talks_slot_id", "talks", ["slot_id"])

    op.create_table(
        "user_slot_selections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("slot_id", sa.BigInteger(), nullable=False),
        sa.Column("talk_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.user_id"],
            name="fk_user_slot_selections_user_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["slots.slot_id"],
            name="fk_user_slot_selections_slot_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["talk_id"], ["talks.talk_id"],
            name="fk_user_slot_selections_talk_id", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "slot_id", name="uq_user_slot_selection"),
    )
    op.create_index("ix_user_slot_selections_user_id", "user_slot_selections", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_slot_selections")
    op.drop_table("talks")
    op.drop_table("slots")
    op.drop_table("events")
