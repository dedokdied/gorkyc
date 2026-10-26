"""web accounts: password hash

Revision ID: 0004_web_auth
Revises: 0003_reminder_sent_at
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_web_auth"
down_revision = "0003_reminder_sent_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
