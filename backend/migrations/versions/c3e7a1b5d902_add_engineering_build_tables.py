"""add engineering build tables

Revision ID: c3e7a1b5d902
Revises: a8d4e6f90123
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3e7a1b5d902"
down_revision: str | None = "a8d4e6f90123"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

build_request_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED",
    name="build_request_status",
)
engineering_run_status = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED",
    name="engineering_run_status",
)
agent_type = postgresql.ENUM(
    "FEATURE_ANALYST", "ARCHITECT", "DEVELOPER", "QA",
    "SECURITY_REVIEWER", "PERFORMANCE_REVIEWER",
    "MAINTAINABILITY_REVIEWER", "TEST_COVERAGE_REVIEWER",
    name="agent_type",
)
agent_step_status = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED",
    name="agent_step_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (build_request_status, engineering_run_status, agent_type, agent_step_status):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "build_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("requirements_document_key", sa.Text(), nullable=True),
        sa.Column("status", build_request_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_build_requests_project_id", "build_requests", ["project_id"], unique=False)

    op.create_table(
        "engineering_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_request_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("status", engineering_run_status, nullable=False),
        sa.Column("current_stage", sa.String(length=100), nullable=True),
        sa.Column("requirements_json", sa.JSON(), nullable=True),
        sa.Column("architecture_json", sa.JSON(), nullable=True),
        sa.Column("review_json", sa.JSON(), nullable=True),
        sa.Column("output_storage_key", sa.String(length=1024), nullable=True),
        sa.Column("fix_iteration", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["build_request_id"], ["build_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_engineering_runs_build_request_id", "engineering_runs", ["build_request_id"], unique=False)
    op.create_index("ix_engineering_runs_project_id", "engineering_runs", ["project_id"], unique=False)

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("engineering_run_id", sa.Uuid(), nullable=False),
        sa.Column("agent_type", agent_type, nullable=False),
        sa.Column("status", agent_step_status, nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["engineering_run_id"], ["engineering_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_steps_engineering_run_id", "agent_steps", ["engineering_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_steps_engineering_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index("ix_engineering_runs_project_id", table_name="engineering_runs")
    op.drop_index("ix_engineering_runs_build_request_id", table_name="engineering_runs")
    op.drop_table("engineering_runs")
    op.drop_index("ix_build_requests_project_id", table_name="build_requests")
    op.drop_table("build_requests")
    bind = op.get_bind()
    for enum in (agent_step_status, agent_type, engineering_run_status, build_request_status):
        enum.drop(bind, checkfirst=True)
