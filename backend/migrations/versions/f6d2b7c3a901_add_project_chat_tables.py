"""add project chat tables

Revision ID: f6d2b7c3a901
Revises: e4b8c2a9d104
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6d2b7c3a901"
down_revision: str | None = "e4b8c2a9d104"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

chat_message_role = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    name="chat_message_role",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN CREATE TYPE chat_message_role AS ENUM ('user', 'assistant', 'system'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        )
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index("ix_chats_project_id", "chats", ["project_id"], unique=True)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("role", chat_message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_chat_id", "chat_messages", ["chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_messages_chat_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chats_project_id", table_name="chats")
    op.drop_table("chats")
    chat_message_role.drop(op.get_bind(), checkfirst=True)
