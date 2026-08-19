from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import EngineeringRunStatus

if TYPE_CHECKING:
    from app.models.agent_step import AgentStep
    from app.models.build_request import BuildRequest
    from app.models.project import Project
    from app.models.project_source import ProjectSource


class EngineeringRun(Base):
    __tablename__ = "engineering_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    build_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("build_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[EngineeringRunStatus] = mapped_column(
        SQLEnum(
            EngineeringRunStatus,
            name="engineering_run_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=EngineeringRunStatus.pending,
        nullable=False,
    )
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requirements_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    architecture_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    review_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    fix_iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    build_request: Mapped["BuildRequest"] = relationship(back_populates="engineering_runs")
    project: Mapped["Project"] = relationship(back_populates="engineering_runs")
    project_source: Mapped["ProjectSource"] = relationship(back_populates="engineering_runs")
    agent_steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="engineering_run",
        cascade="all, delete-orphan",
        order_by="AgentStep.started_at",
    )
