import uuid
import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class SkillLevel(str, enum.Enum):
    VERIFIED = "verified"       # Confirmed by both resume and GitHub evidence
    PARTIAL = "partial"         # Mentioned but weak evidence
    MISSING = "missing"         # Required by JD but absent from candidate profile
    UNSUPPORTED = "unsupported" # Claimed in resume but no GitHub evidence


class Skill(UUIDMixin, TimestampMixin, Base):
    """
    Master skill catalogue.  Populated lazily as skills are discovered
    from AI service responses.
    """

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("name", name="uq_skill_name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    candidate_skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill", back_populates="skill"
    )

    def __repr__(self) -> str:
        return f"<Skill name={self.name!r}>"


class CandidateSkill(UUIDMixin, TimestampMixin, Base):
    """
    A skill attributed to a candidate within a specific analysis.
    Stores the confidence score and verification level returned by the AI services.
    """

    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("analysis_id", "skill_id", name="uq_candidate_skill"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[SkillLevel] = mapped_column(
        SAEnum(SkillLevel, name="skilllevel"),
        nullable=False,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="candidate_skills"
    )
    skill: Mapped["Skill"] = relationship("Skill", back_populates="candidate_skills")

    def __repr__(self) -> str:
        return (
            f"<CandidateSkill analysis={self.analysis_id} "
            f"skill={self.skill_id} level={self.level}>"
        )
