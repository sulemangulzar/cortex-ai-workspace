"""replace old domain tables with run schema

Revision ID: e4b8c2a9d104
Revises: c3e7a1b5d902
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e4b8c2a9d104"
down_revision: str | None = "c3e7a1b5d902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

run_status = postgresql.ENUM("pending", "running", "needs_revision", "success", "failed", name="run_status", create_type=False)
task_status = postgresql.ENUM("pending", "running", "success", "failed", name="task_status", create_type=False)
finding_severity = postgresql.ENUM("low", "med", "high", "critical", name="finding_severity", create_type=False)
execution_log_source = postgresql.ENUM("tool_output", "agent_reasoning", name="execution_log_source", create_type=False)


def _create_enum(name: str, values: str) -> None:
    op.execute(sa.text(f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({values}); EXCEPTION WHEN duplicate_object THEN NULL; END $$;"))


def _drop_enum(name: str) -> None:
    op.execute(sa.text(f"DROP TYPE IF EXISTS {name} CASCADE"))


def upgrade() -> None:
    for table in (
        "execution_logs",
        "review_findings",
        "code_files",
        "architecture_docs",
        "features",
        "agent_tasks",
        "runs",
        "requirement_docs",
        "agent_steps",
        "engineering_runs",
        "build_requests",
        "project_versions",
        "chat_messages",
        "chats",
        "project_sources",
        "projects",
    ):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    for enum_name in (
        "run_status",
        "task_status",
        "finding_severity",
        "execution_log_source",
        "build_request_status",
        "engineering_run_status",
        "agent_step_status",
        "agent_type",
        "project_status",
        "project_source_status",
        "source_type",
        "roles",
    ):
        _drop_enum(enum_name)

    _create_enum("run_status", "'pending', 'running', 'needs_revision', 'success', 'failed'")
    _create_enum("task_status", "'pending', 'running', 'success', 'failed'")
    _create_enum("finding_severity", "'low', 'med', 'high', 'critical'")
    _create_enum("execution_log_source", "'tool_output', 'agent_reasoning'")

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)

    op.create_table(
        "requirement_docs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requirement_docs_project_id", "requirement_docs", ["project_id"], unique=False)

    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("status", run_status, nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_project_id", "runs", ["project_id"], unique=False)

    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("input", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("tool_output", sa.Text(), nullable=True),
        sa.Column("revision_cycle", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tasks_run_id", "agent_tasks", ["run_id"], unique=False)

    op.create_table("features", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(length=255), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("source_ref", sa.String(length=1024), nullable=True), sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_features_run_id", "features", ["run_id"], unique=False)

    op.create_table("architecture_docs", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("content_json", sa.JSON(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_architecture_docs_run_id", "architecture_docs", ["run_id"], unique=False)

    op.create_table("code_files", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("path", sa.String(length=1024), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("revision_cycle", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_code_files_run_id", "code_files", ["run_id"], unique=False)

    op.create_table("review_findings", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("reviewer_agent", sa.String(length=100), nullable=False), sa.Column("severity", finding_severity, nullable=False), sa.Column("file_ref", sa.String(length=1024), nullable=True), sa.Column("line_ref", sa.Integer(), nullable=True), sa.Column("message", sa.Text(), nullable=False), sa.Column("resolved", sa.Boolean(), nullable=False), sa.Column("revision_cycle", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_review_findings_run_id", "review_findings", ["run_id"], unique=False)

    op.create_table("execution_logs", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("source", execution_log_source, nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_execution_logs_run_id", "execution_logs", ["run_id"], unique=False)


def downgrade() -> None:
    for table in ("execution_logs", "review_findings", "code_files", "architecture_docs", "features", "agent_tasks", "runs", "requirement_docs", "projects"):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    for enum_name in ("execution_log_source", "finding_severity", "task_status", "run_status"):
        _drop_enum(enum_name)
