"""track sent reminders

Revision ID: 0003_reminder_sent_at
Revises: 0002_align_with_plan
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_reminder_sent_at"
down_revision = "0002_align_with_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "events_pending_reminders_idx",
        "events",
        ["due_at"],
        postgresql_where=sa.text(
            "type = 'reminder' AND status = 'planned' AND reminder_sent_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("events_pending_reminders_idx", table_name="events")
    op.drop_column("events", "reminder_sent_at")
