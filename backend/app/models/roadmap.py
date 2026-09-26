import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class RoadmapSkillClassification(str, enum.Enum):
    MISSING = "missing"
    PARTIAL = "partial"


class RoadmapSkillState(str, enum.Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    LEARNING = "learning"
    LEARNING_COMPLETED = "learning_completed"
    MINI_PROJECT_AVAILABLE = "mini_project_available"
    PROJECT_IN_PROGRESS = "project_in_progress"
    PROJECT_SUBMITTED = "project_submitted"
    ASSESSMENT_AVAILABLE = "assessment_available"
    ASSESSMENT_STARTED = "assessment_started"
    VERIFIED = "verified"
    TARGETED_REVIEW = "targeted_review"
    RETAKE_AVAILABLE = "retake_available"


class Roadmap(UUIDMixin, TimestampMixin, Base):
    """
    Top-level roadmap for a candidate analysis.
    Stores the skill-level learning model rather than the legacy weekly roadmap.
    """

    __tablename__ = "roadmaps"

    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    analysis: Mapped[Optional["Analysis"]] = relationship(
        "Analysis",
        back_populates="roadmap",
    )
    skills: Mapped[List["RoadmapSkillRecord"]] = relationship(
        "RoadmapSkillRecord",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapSkillRecord.created_at",
    )

    def __repr__(self) -> str:
        return f"<Roadmap analysis={self.analysis_id}>"


class RoadmapSkillRecord(UUIDMixin, TimestampMixin, Base):
    """A single skill entry in the roadmap."""

    __tablename__ = "roadmap_skills"

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    classification: Mapped[RoadmapSkillClassification] = mapped_column(
        SAEnum(RoadmapSkillClassification, name="roadmapskillclassification"),
        nullable=False,
        index=True,
    )
    state: Mapped[RoadmapSkillState] = mapped_column(
        SAEnum(RoadmapSkillState, name="roadmapskillstate"),
        default=RoadmapSkillState.LOCKED,
        nullable=False,
        index=True,
    )
    learning_track: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    mini_project: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    assessment: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    prerequisites: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    roadmap: Mapped["Roadmap"] = relationship("Roadmap", back_populates="skills")

    def __repr__(self) -> str:
        return (
            f"<RoadmapSkillRecord name={self.name!r} "
            f"classification={self.classification} state={self.state}>"
        )


class RoadmapStep(UUIDMixin, TimestampMixin, Base):
    """
    Legacy compatibility model retained to avoid breaking older orchestration
    code while the roadmap module migrates to the new skill-based model.
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

    roadmap: Mapped["Roadmap"] = relationship("Roadmap")

    def __repr__(self) -> str:
        return f"<RoadmapStep week={self.week} topic={self.topic!r}>"
