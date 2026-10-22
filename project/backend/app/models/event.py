import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

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


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, native_enum=False, values_callable=_enum_values, name="eventtype"),
        nullable=False,
    )
    status: Mapped[EventStatus] = mapped_column(
        SAEnum(EventStatus, native_enum=False, values_callable=_enum_values, name="eventstatus"),
        nullable=False,
        default=EventStatus.planned,
        server_default=text("'planned'"),
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="Europe/Moscow",
        server_default=text("'Europe/Moscow'"),
    )
    source: Mapped[EventSource] = mapped_column(
        SAEnum(EventSource, native_enum=False, values_callable=_enum_values, name="eventsource"),
        nullable=False,
        default=EventSource.text,
        server_default=text("'text'"),
    )
    recurrence: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    search_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('russian', search_text)", persisted=True),
        nullable=True,
    )
    # Векторный поиск отложен: в демо-окружении нет расширения pgvector.
    # См. docs/decisions/0002-vector-search-deferred.md. Колонка хранит
    # сериализованный вектор, чтобы не менять контракт API при включении флага.
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at",
            name="events_time_check",
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0",
            name="events_duration_check",
        ),
        CheckConstraint(
            "type <> 'meeting' OR (starts_at IS NOT NULL AND ends_at IS NOT NULL)",
            name="meetings_time_check",
        ),
        CheckConstraint(
            "type IN ('task', 'meeting', 'reminder')",
            name="events_type_check",
        ),
        CheckConstraint(
            "status IN ('planned', 'done', 'cancelled')",
            name="events_status_check",
        ),
        CheckConstraint(
            "source IN ('text', 'voice', 'import')",
            name="events_source_check",
        ),
        ExcludeConstraint(
            (Column("user_id"), "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            using="gist",
            where=text("type = 'meeting' AND status = 'planned' AND starts_at IS NOT NULL"),
            name="meetings_no_overlap",
        ),
        Index("events_user_time_idx", "user_id", "starts_at"),
        Index("events_user_due_idx", "user_id", "due_at"),
        Index(
            "events_pending_reminders_idx",
            "due_at",
            postgresql_where=text(
                "type = 'reminder' AND status = 'planned' AND reminder_sent_at IS NULL"
            ),
        ),
        Index("events_tsv_idx", "tsv", postgresql_using="gin"),
        Index(
            "events_trgm_idx",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )
