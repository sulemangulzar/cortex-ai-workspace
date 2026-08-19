"""require usernames for users

Revision ID: f2a7c9d4e801
Revises: 5592dae1fe4b
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f2a7c9d4e801"
down_revision: str | None = "5592dae1fe4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Give legacy rows a deterministic username before enforcing the constraint.
    op.execute(
        sa.text(
            "UPDATE users "
            "SET username = 'user_' || substr(replace(id::text, '-', ''), 1, 42) "
            "WHERE username IS NULL"
        )
    )
    op.alter_column("users", "username", existing_type=sa.String(length=50), nullable=False)


def downgrade() -> None:
    op.alter_column("users", "username", existing_type=sa.String(length=50), nullable=True)
