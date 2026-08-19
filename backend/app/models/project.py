from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from app.models.base import Base

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.build_request import BuildRequest
    from app.models.chat import Chat
    from app.models.engineering_run import EngineeringRun
    from app.models.project_source import ProjectSource


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(
            ProjectStatus,
            name="project_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ProjectStatus.created,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sources: Mapped[list["ProjectSource"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    chats: Mapped[list["Chat"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    build_requests: Mapped[list["BuildRequest"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    engineering_runs: Mapped[list["EngineeringRun"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

