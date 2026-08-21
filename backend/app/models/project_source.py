from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.enums import ProjectSourceStatus, SourceType

if TYPE_CHECKING:
    from app.models.project import Project


class ProjectSource(Base):
    __tablename__ = "project_sources"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    source_type: Mapped[SourceType] = mapped_column(
        SQLEnum(
            SourceType,
            name="source_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )

    bucket: Mapped[str] = mapped_column(
        String(255),
        default="cortex-workspace",
        nullable=False,
    )

    object_path: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    status: Mapped[ProjectSourceStatus] = mapped_column(
        SQLEnum(
            ProjectSourceStatus,
            name="project_source_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ProjectSourceStatus.uploading,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped["Project"] = relationship(back_populates="sources")

