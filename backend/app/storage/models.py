"""SQLAlchemy ORM models — canonical schema in docs/12-session-storage.md."""

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    started_at: Mapped[str] = mapped_column(Text)
    ended_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    interview_mode: Mapped[str] = mapped_column(Text, default="technical_project_walkthrough")
    persona: Mapped[str] = mapped_column(Text, default="senior_colleague")
    transcript_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    debrief_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_kind: Mapped[str | None] = mapped_column(Text, nullable=True)  # minimal | full
    status: Mapped[str] = mapped_column(Text, default="in_progress")  # in_progress|completed|failed
    review_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text)


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_interview_id: Mapped[str] = mapped_column(
        Text, ForeignKey("interview_sessions.id"), nullable=False
    )
    started_at: Mapped[str] = mapped_column(Text)
    ended_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona: Mapped[str] = mapped_column(Text, default="recruiter_friend")
    transcript_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(Text, default="in_progress")
    created_at: Mapped[str] = mapped_column(Text)


class VocabularyEntry(Base):
    __tablename__ = "vocabulary_bank"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    term_en: Mapped[str] = mapped_column(Text, index=True)
    translation_ru: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text, default="word")  # word | phrase | collocation
    example_en: Mapped[str] = mapped_column(Text)
    context_note_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[str] = mapped_column(Text, index=True)
    category: Mapped[str] = mapped_column(Text, default="technical")
    # soft delete: status='deleted' keeps the row for the "don't re-add" dedup rule (doc 10/12)
    status: Mapped[str] = mapped_column(Text, default="new", index=True)
    times_seen: Mapped[int] = mapped_column(Integer, default=1)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)
