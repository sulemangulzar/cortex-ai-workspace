"""add cancelled statuses

Revision ID: a1b2c3d4e905
Revises: f6d2b7c3a901
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e905"
down_revision: str | None = "f6d2b7c3a901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE run_status ADD VALUE IF NOT EXISTS 'cancelled'"))
    op.execute(sa.text("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'cancelled'"))


def downgrade() -> None:
    # PostgreSQL cannot remove enum values without recreating the type. Keep this
    # downgrade intentionally no-op to avoid unsafe data rewrites.
    pass
