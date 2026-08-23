from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import FindingSeverity


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewer_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        SQLEnum(FindingSeverity, name="finding_severity", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    file_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_ref: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_cycle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run = relationship("Run", back_populates="review_findings")
