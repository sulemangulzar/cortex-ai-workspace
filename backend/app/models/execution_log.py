from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ExecutionLogSource


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    source: Mapped[ExecutionLogSource] = mapped_column(
        SQLEnum(ExecutionLogSource, name="execution_log_source", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run = relationship("Run", back_populates="execution_logs")
