from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_sources.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    object_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    instruction: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    change_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
