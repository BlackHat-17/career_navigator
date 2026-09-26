import uuid
import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.skill import CandidateSkill
    from app.models.evidence import Evidence
    from app.models.project import Project, RecommendedProject
    from app.models.roadmap import Roadmap


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Analysis(UUIDMixin, TimestampMixin, Base):
    """
    Top-level record that tracks a full candidate analysis run.

    Stores the raw inputs and the aggregated outputs from every AI service
    so the frontend can retrieve previous results without re-running anything.
    """

    __tablename__ = "analyses"

    # ── Foreign keys ─────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Status lifecycle ─────────────────────────────────────────────────
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus, name="analysisstatus"),
        default=AnalysisStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Input snapshot ───────────────────────────────────────────────────
    github_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Raw service outputs (stored as JSON blobs) ─────────────────────
    github_agent_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    resume_judge_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    project_recommender_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    roadmap_generator_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # ── Computed summary ─────────────────────────────────────────────────
    skill_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    major_gaps: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="analyses")

    candidate_skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill", back_populates="analysis", cascade="all, delete-orphan"
    )
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="analysis", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="analysis", cascade="all, delete-orphan"
    )
    recommended_projects: Mapped[List["RecommendedProject"]] = relationship(
        "RecommendedProject", back_populates="analysis", cascade="all, delete-orphan"
    )
    roadmap: Mapped[Optional["Roadmap"]] = relationship(
        "Roadmap", back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} status={self.status} user_id={self.user_id}>"
