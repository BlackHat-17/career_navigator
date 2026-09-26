import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Roadmap(UUIDMixin, TimestampMixin, Base):
    """
    The top-level learning roadmap generated for a candidate.
    One-to-one with Analysis.
    """

    __tablename__ = "roadmaps"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    career_goal: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="roadmap")
    steps: Mapped[List["RoadmapStep"]] = relationship(
        "RoadmapStep",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapStep.week",
    )

    def __repr__(self) -> str:
        return f"<Roadmap goal={self.career_goal!r} analysis={self.analysis_id}>"


class RoadmapStep(UUIDMixin, TimestampMixin, Base):
    """
    A single week / phase within a Roadmap.
    Stores topics, resources and a milestone returned by the Roadmap Generator.
    """

    __tablename__ = "roadmap_steps"

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    week: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resources: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    milestone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills_covered: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    roadmap: Mapped["Roadmap"] = relationship("Roadmap", back_populates="steps")

    def __repr__(self) -> str:
        return f"<RoadmapStep week={self.week} topic={self.topic!r}>"
