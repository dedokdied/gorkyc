"""align sessions/messages/pending_actions with the plan, add web reminders

Revision ID: 0007_schema_align
Revises: 0006_telegram_link
Create Date: 2026-10-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_schema_align"
down_revision = "0006_telegram_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A conversation can come from the web or Telegram. external_id keeps the
    # client-side identifier (Telegram chat id, browser session id) so history
    # can be traced back to the channel it came from.
    op.add_column("sessions", sa.Column("channel", sa.String(length=16), nullable=True))
    op.add_column("sessions", sa.Column("external_id", sa.String(length=255), nullable=True))
    op.create_index(
        "sessions_channel_external_idx",
        "sessions",
        ["channel", "external_id"],
    )

    # Tool calls are not shown in the UI yet, but storing them keeps the full
    # dialogue reproducible without a second table.
    op.add_column("messages", sa.Column("tool_name", sa.String(length=64), nullable=True))
    op.add_column("messages", sa.Column("tool_payload", postgresql.JSONB(), nullable=True))

    # The in-memory pending action carried the question and quick options.
    op.add_column("pending_actions", sa.Column("question", sa.Text(), nullable=True))
    op.add_column(
        "pending_actions",
        sa.Column(
            "options",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )

    # In-app reminder banner: an acknowledged reminder disappears from the web
    # inbox without touching Telegram delivery state.
    op.add_column("events", sa.Column("web_ack_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "events_web_inbox_idx",
        "events",
        ["user_id", "due_at"],
        postgresql_where=sa.text(
            "type = 'reminder' AND status = 'planned' AND web_ack_at IS NULL"
        ),
    )

    # Onboarding must survive a bot restart; MemoryStorage does not.
    op.add_column(
        "users",
        sa.Column(
            "onboarding_seen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_seen")
    op.drop_index("events_web_inbox_idx", table_name="events")
    op.drop_column("events", "web_ack_at")

    op.drop_column("pending_actions", "options")
    op.drop_column("pending_actions", "question")

    op.drop_column("messages", "tool_payload")
    op.drop_column("messages", "tool_name")

    op.drop_index("sessions_channel_external_idx", table_name="sessions")
    op.drop_column("sessions", "external_id")
    op.drop_column("sessions", "channel")
