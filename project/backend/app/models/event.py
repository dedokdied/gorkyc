import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.models import Base


class EventType(str, enum.Enum):
    task = "task"
    meeting = "meeting"
    reminder = "reminder"


class EventStatus(str, enum.Enum):
    planned = "planned"
    done = "done"
    cancelled = "cancelled"


class EventSource(str, enum.Enum):
    text = "text"
    voice = "voice"
    import_ = "import"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[EventType] = mapped_column(SAEnum(EventType, native_enum=False), nullable=False)
    status: Mapped[EventStatus] = mapped_column(SAEnum(EventStatus, native_enum=False), nullable=False, default=EventStatus.planned)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="Europe/Moscow")
    source: Mapped[EventSource] = mapped_column(SAEnum(EventSource, native_enum=False), nullable=False, default=EventSource.text)
    recurrence: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tsv: Mapped[str | None] = mapped_column(Text, Computed("to_tsvector('russian', search_text)", persisted=True), nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at", name="events_time_check"),
        CheckConstraint("duration_minutes IS NULL OR duration_minutes > 0", name="events_duration_check"),
    )
