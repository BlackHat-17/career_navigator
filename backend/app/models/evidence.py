import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Evidence(UUIDMixin, TimestampMixin, Base):
    """
    A single piece of evidence that supports a skill claim.
    Evidence items are returned by the GitHub Agent and Resume Judge and
    stored here for display in the frontend.

    Examples:
      - source="github"  snippet="Flask backend in repo career-api"
      - source="resume"  snippet="3 years FastAPI experience"
    """

    __tablename__ = "evidence"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Which skill this evidence supports (free-text name, no FK to allow
    # skills that haven't yet been normalised into the catalogue)
    skill_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Where the evidence comes from
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "github" | "resume" | "job_description"

    # Human-readable snippet, e.g. a repo name or resume sentence
    snippet: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: link to the source (e.g. GitHub repo URL)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="evidence_items"
    )

    def __repr__(self) -> str:
        return (
            f"<Evidence analysis={self.analysis_id} "
            f"skill={self.skill_name!r} source={self.source!r}>"
        )
