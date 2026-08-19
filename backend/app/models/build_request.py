from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BuildRequestStatus

if TYPE_CHECKING:
    from app.models.engineering_run import EngineeringRun
    from app.models.project import Project


class BuildRequest(Base):
    __tablename__ = "build_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_document_key: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[BuildRequestStatus] = mapped_column(
        SQLEnum(
            BuildRequestStatus,
            name="build_request_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=BuildRequestStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped["Project"] = relationship(back_populates="build_requests")
    engineering_runs: Mapped[list["EngineeringRun"]] = relationship(
        back_populates="build_request",
        cascade="all, delete-orphan",
    )
