from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RunStatus

if TYPE_CHECKING:
    from app.models.agent_task import AgentTask
    from app.models.architecture_doc import ArchitectureDoc
    from app.models.code_file import CodeFile
    from app.models.execution_log import ExecutionLog
    from app.models.feature import Feature
    from app.models.project import Project



class Run(Base):
    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, name="run_status", values_callable=lambda enum: [item.value for item in enum]),
        default=RunStatus.pending,
        nullable=False,
    )
    revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="runs")
    agent_tasks: Mapped[list["AgentTask"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    features: Mapped[list["Feature"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    architecture_docs: Mapped[list["ArchitectureDoc"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    code_files: Mapped[list["CodeFile"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    review_findings: Mapped[list[Any]] = relationship("ReviewFinding", back_populates="run", cascade="all, delete-orphan")
    execution_logs: Mapped[list["ExecutionLog"]] = relationship(back_populates="run", cascade="all, delete-orphan")
