"""search: fold Cyrillic independently of the database collation

Revision ID: 0005_search_casefold
Revises: 0004_web_auth
Create Date: 2026-10-25
"""

from alembic import op

revision = "0005_search_casefold"
down_revision = "0004_web_auth"
branch_labels = None
depends_on = None

CYRILLIC_UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
CYRILLIC_LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def _folded_search_text() -> str:
    return (
        "lower(translate(search_text, "
        f"'{CYRILLIC_UPPER}', '{CYRILLIC_LOWER}'))"
    )


def upgrade() -> None:
    # PostgreSQL lower()/to_tsvector() use the database collation. On a
    # cluster initialized with --locale=C they keep Cyrillic uppercase, so
    # "Договор" never matches "договор". Normalize the text explicitly.
    op.execute("DROP INDEX IF EXISTS events_tsv_idx")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS tsv")
    op.execute(
        "ALTER TABLE events ADD COLUMN tsv tsvector "
        f"GENERATED ALWAYS AS (to_tsvector('russian', {_folded_search_text()})) STORED"
    )
    op.execute("CREATE INDEX events_tsv_idx ON events USING gin (tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS events_tsv_idx")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS tsv")
    op.execute(
        "ALTER TABLE events ADD COLUMN tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('russian', search_text)) STORED"
    )
    op.execute("CREATE INDEX events_tsv_idx ON events USING gin (tsv)")
