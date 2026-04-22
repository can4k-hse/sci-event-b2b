"""talks: replace speaker (varchar) with speakers (JSON array)

Revision ID: 003
Revises: 002
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("talks", "speaker")
    op.add_column("talks", sa.Column("speakers", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("talks", "speakers")
    op.add_column("talks", sa.Column("speaker", sa.String(length=255), nullable=True))
