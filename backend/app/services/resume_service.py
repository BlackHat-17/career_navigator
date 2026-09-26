"""
ResumeService
─────────────
Handles file validation, text extraction stub, and delegation to the
Resume Judge service.

Responsibilities:
  1. Validate MIME type and file size
  2. Save the file to the configured upload directory
  3. Extract plain text from the file (PDF / DOCX)
  4. Forward to ResumeJudgeClient
  5. Persist raw output to the Analysis record
  6. Return structured response

The service does NOT implement any judging or scoring logic.
"""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.resume_judge_client import ResumeJudgeClient
from app.core.config import get_settings
from app.core.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisStatus
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.resume import ResumeAnalysisRead, ResumeAnalyzeRequest, ResumeFeedback, ResumeSkillClaim

logger = get_logger(__name__)
settings = get_settings()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}


class ResumeService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def analyze(
        self,
        request: ResumeAnalyzeRequest,
        resume_file: UploadFile,
    ) -> ResumeAnalysisRead:
        # 1. Validate user
        user = await self._db.get(User, request.user_id)
        if not user:
            raise NotFoundError(f"User {request.user_id} not found.")

        # 2. Validate file
        await self._validate_file(resume_file)

        # 3. Read bytes and save
        content = await resume_file.read()
        safe_filename = self._safe_filename(resume_file.filename or "resume")
        saved_path = await self._save_file_static(safe_filename, content)
        logger.info("Resume saved to %s", saved_path)

        # 4. Extract text (best-effort; service is responsible for deep parsing)
        resume_text = self._extract_text(
            content, resume_file.content_type or ""
        )

        # 5. Create analysis record
        analysis = Analysis(
            user_id=request.user_id,
            target_role=request.target_role,
            resume_filename=safe_filename,
            status=AnalysisStatus.PROCESSING,
        )
        self._db.add(analysis)
        await self._db.flush()
        logger.info("Resume analysis started id=%s", analysis.id)

        # 6. Call Resume Judge
        try:
            async with ResumeJudgeClient() as client:
                raw = await client.analyze_resume(
                    target_role=request.target_role,
                    resume_text=resume_text,
                )
        except Exception as exc:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            await self._db.flush()
            raise

        # 7. Persist
        analysis.resume_judge_output = raw
        analysis.status = AnalysisStatus.COMPLETED

        # Persist evidence items from resume claims
        for claim in raw.get("claimed_skills", []):
            evidence = Evidence(
                analysis_id=analysis.id,
                skill_name=claim.get("name", ""),
                source="resume",
                snippet=claim.get("context", claim.get("name", "")),
            )
            self._db.add(evidence)

        await self._db.flush()
        logger.info("Resume analysis completed id=%s", analysis.id)

        # 8. Build response
        claimed_skills = [
            ResumeSkillClaim(**c) for c in raw.get("claimed_skills", [])
        ]
        feedback = [
            ResumeFeedback(**f) for f in raw.get("feedback", [])
        ]

        return ResumeAnalysisRead(
            analysis_id=analysis.id,
            user_id=request.user_id,
            target_role=request.target_role,
            resume_filename=safe_filename,
            claimed_skills=claimed_skills,
            feedback=feedback,
            overall_score=raw.get("overall_score"),
            raw=raw,
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    async def _validate_file(self, file: UploadFile) -> None:
        ext = Path(file.filename or "").suffix.lower()
        mime = (file.content_type or "").split(";")[0].strip()

        if ext not in ALLOWED_EXTENSIONS and mime not in ALLOWED_MIME_TYPES:
            raise InvalidFileTypeError(
                f"File type '{mime or ext}' is not supported. "
                f"Allowed: PDF, DOC, DOCX."
            )

        # Peek at file size without consuming the whole stream
        # FastAPI makes the file available via .read(); we'll read it once
        # in the caller and pass bytes in.
        # Size check is done after full read in analyze().
        pass  # size validated after content read

    async def _save_file(self, filename: str, content: bytes) -> str:
        return await ResumeService._save_file_static(filename, content)

    @staticmethod
    async def _save_file_static(filename: str, content: bytes) -> str:
        if len(content) > settings.max_upload_bytes:
            raise FileTooLargeError(
                f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )
        upload_dir = Path(settings.UPLOAD_DIR)
        
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest = upload_dir / filename
            dest.write_bytes(content)
            logger.info(f"Saved resume to {dest}")
            return str(dest)
        except PermissionError as e:
            # Fallback to /app/uploads in case /tmp is not writable
            logger.warning(f"Permission denied for {upload_dir}, using fallback: {e}")
            fallback_dir = Path("/app/uploads")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            dest = fallback_dir / filename
            dest.write_bytes(content)
            logger.info(f"Saved resume to fallback location {dest}")
            return str(dest)

    @staticmethod
    def _safe_filename(original: str) -> str:
        stem = Path(original).stem
        suffix = Path(original).suffix.lower()
        # Strip non-alphanumeric characters from stem
        safe_stem = "".join(c for c in stem if c.isalnum() or c in "-_")[:80]
        unique = uuid.uuid4().hex[:8]
        return f"{safe_stem}_{unique}{suffix}"

    @staticmethod
    def _extract_text(content: bytes, mime: str) -> str:
        """
        Best-effort plain-text extraction.
        The Resume Judge service will do its own deeper parsing;
        this is just a convenience to avoid sending binary data over HTTP.
        """
        try:
            if "pdf" in mime:
                import PyPDF2  # type: ignore
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                return "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            elif "word" in mime or "docx" in mime or "document" in mime:
                import docx  # type: ignore
                doc = docx.Document(io.BytesIO(content))
                return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            logger.warning("Text extraction failed (%s), sending empty text: %s", mime, exc)
        return ""
