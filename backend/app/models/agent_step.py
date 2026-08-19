from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AgentStepStatus, AgentType

if TYPE_CHECKING:
    from app.models.engineering_run import EngineeringRun


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    engineering_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("engineering_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(
            AgentType,
            name="agent_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    status: Mapped[AgentStepStatus] = mapped_column(
        SQLEnum(
            AgentStepStatus,
            name="agent_step_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=AgentStepStatus.pending,
        nullable=False,
    )
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    engineering_run: Mapped["EngineeringRun"] = relationship(
        back_populates="agent_steps"
    )
