import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Project(UUIDMixin, TimestampMixin, Base):
    """
    An existing project discovered from the candidate's GitHub profile
    by the GitHub Agent.
    """

    __tablename__ = "projects"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    languages: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    topics: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="projects")

    def __repr__(self) -> str:
        return f"<Project name={self.name!r} analysis={self.analysis_id}>"


class RecommendedProject(UUIDMixin, TimestampMixin, Base):
    """
    A project recommended by the Project Recommender service for a candidate
    to build in order to close their skill gaps.
    """

    __tablename__ = "recommended_projects"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="recommended_projects"
    )

    def __repr__(self) -> str:
        return f"<RecommendedProject title={self.title!r} analysis={self.analysis_id}>"
