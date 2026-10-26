"""telegram link: shared profile between web and bot

Revision ID: 0006_telegram_link
Revises: 0005_search_casefold
Create Date: 2026-10-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_telegram_link"
down_revision = "0005_search_casefold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.String(), nullable=True))

    # Existing bot users already carry the canonical id in openclaw_peer_id.
    op.execute(
        "UPDATE users "
        "SET telegram_id = substring(openclaw_peer_id from 10)::bigint "
        "WHERE openclaw_peer_id LIKE 'telegram:%' "
        "AND substring(openclaw_peer_id from 10) ~ '^[0-9]+$'"
    )
    op.create_index(
        "users_telegram_id_key",
        "users",
        ["telegram_id"],
        unique=True,
    )

    op.create_table(
        "telegram_link_codes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(length=5), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_telegram_link_codes_telegram_id",
        "telegram_link_codes",
        ["telegram_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_telegram_link_codes_telegram_id", table_name="telegram_link_codes")
    op.drop_table("telegram_link_codes")
    op.drop_index("users_telegram_id_key", table_name="users")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_id")
