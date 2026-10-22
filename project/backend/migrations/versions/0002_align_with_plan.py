"""align schema with PLAN.md and the API contract

Revision ID: 0002_align_with_plan
Revises: 79729d8e99a6
Create Date: 2026-10-22
"""

from alembic import op

revision = "0002_align_with_plan"
down_revision = "79729d8e99a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Source enum used to store the Python attribute name ("import_"); the
    # contract and the model use the value "import".
    op.execute("UPDATE events SET source = 'import' WHERE source = 'import_'")
    op.execute("ALTER TABLE events ALTER COLUMN source TYPE varchar(6)")

    # JSON -> JSONB and TEXT -> TSVECTOR.
    op.execute("ALTER TABLE events ALTER COLUMN metadata TYPE jsonb USING metadata::jsonb")
    op.execute("ALTER TABLE events ALTER COLUMN embedding TYPE jsonb USING embedding::jsonb")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN slots TYPE jsonb USING slots::jsonb")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS tsv")
    op.execute(
        "ALTER TABLE events ADD COLUMN tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('russian', search_text)) STORED"
    )

    # pending_actions.missing: JSON array -> text[].
    op.execute("ALTER TABLE pending_actions ADD COLUMN missing_new text[]")
    op.execute(
        "UPDATE pending_actions "
        "SET missing_new = COALESCE(ARRAY(SELECT json_array_elements_text(missing)), '{}'::text[]) "
        "WHERE missing IS NOT NULL"
    )
    op.execute("UPDATE pending_actions SET missing_new = '{}'::text[] WHERE missing_new IS NULL")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN missing_new SET DEFAULT '{}'::text[]")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN missing_new SET NOT NULL")
    op.execute("ALTER TABLE pending_actions DROP COLUMN missing")
    op.execute("ALTER TABLE pending_actions RENAME COLUMN missing_new TO missing")

    # Server defaults expected by the model and PLAN.md.
    op.execute("ALTER TABLE events ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE events ALTER COLUMN status SET DEFAULT 'planned'")
    op.execute("ALTER TABLE events ALTER COLUMN timezone SET DEFAULT 'Europe/Moscow'")
    op.execute("ALTER TABLE events ALTER COLUMN source SET DEFAULT 'text'")
    op.execute("ALTER TABLE events ALTER COLUMN metadata SET DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE events ALTER COLUMN search_text SET DEFAULT ''")
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE users ALTER COLUMN display_name SET DEFAULT 'demo'")
    op.execute("ALTER TABLE users ALTER COLUMN timezone SET DEFAULT 'Europe/Moscow'")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN slots SET DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN missing SET DEFAULT '{}'::text[]")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN is_active SET DEFAULT true")
    op.execute(
        "ALTER TABLE pending_actions ALTER COLUMN expires_at "
        "SET DEFAULT now() + interval '30 minutes'"
    )

    # Only one active pending action per session. Keep the newest one.
    op.execute(
        "UPDATE pending_actions p SET is_active = false "
        "WHERE p.is_active AND EXISTS ("
        "  SELECT 1 FROM pending_actions q "
        "  WHERE q.session_key = p.session_key AND q.is_active "
        "    AND (q.created_at > p.created_at "
        "         OR (q.created_at = p.created_at AND q.id > p.id))"
        ")"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS pending_one_active_idx "
        "ON pending_actions (session_key) WHERE is_active"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS pending_session_idx "
        "ON pending_actions (session_key, created_at)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS events_user_time_idx ON events (user_id, starts_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS events_user_due_idx ON events (user_id, due_at)")
    op.execute("CREATE INDEX IF NOT EXISTS events_tsv_idx ON events USING gin (tsv)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS events_trgm_idx "
        "ON events USING gin (search_text gin_trgm_ops)"
    )

    # Enum/slot checks. NOT VALID keeps the migration safe for legacy rows while
    # still enforcing the rules for every new or updated row.
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'events_type_check') THEN "
        "ALTER TABLE events ADD CONSTRAINT events_type_check "
        "CHECK (type IN ('task', 'meeting', 'reminder')) NOT VALID; "
        "END IF; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'events_status_check') THEN "
        "ALTER TABLE events ADD CONSTRAINT events_status_check "
        "CHECK (status IN ('planned', 'done', 'cancelled')) NOT VALID; "
        "END IF; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'events_source_check') THEN "
        "ALTER TABLE events ADD CONSTRAINT events_source_check "
        "CHECK (source IN ('text', 'voice', 'import')) NOT VALID; "
        "END IF; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'meetings_time_check') THEN "
        "ALTER TABLE events ADD CONSTRAINT meetings_time_check "
        "CHECK (type <> 'meeting' OR (starts_at IS NOT NULL AND ends_at IS NOT NULL)) NOT VALID; "
        "END IF; END $$"
    )

    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'meetings_no_overlap') THEN "
        "ALTER TABLE events ADD CONSTRAINT meetings_no_overlap "
        "EXCLUDE USING gist (user_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) "
        "WHERE (type = 'meeting' AND status = 'planned' AND starts_at IS NOT NULL); "
        "END IF; END $$"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS events_trgm_idx")
    op.execute("DROP INDEX IF EXISTS events_tsv_idx")
    op.execute("DROP INDEX IF EXISTS events_user_due_idx")
    op.execute("DROP INDEX IF EXISTS events_user_time_idx")
    op.execute("DROP INDEX IF EXISTS pending_session_idx")
    op.execute("DROP INDEX IF EXISTS pending_one_active_idx")

    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS meetings_no_overlap")
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS meetings_time_check")
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS events_source_check")
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS events_status_check")
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS events_type_check")

    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS tsv")
    op.execute(
        "ALTER TABLE events ADD COLUMN tsv text "
        "GENERATED ALWAYS AS (to_tsvector('russian', search_text)) STORED"
    )

    op.execute("ALTER TABLE events ALTER COLUMN metadata TYPE json USING metadata::json")
    op.execute("ALTER TABLE events ALTER COLUMN embedding TYPE json USING embedding::json")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN slots TYPE json USING slots::json")

    op.execute("ALTER TABLE pending_actions ADD COLUMN missing_old json")
    op.execute("UPDATE pending_actions SET missing_old = to_json(missing)")
    op.execute("ALTER TABLE pending_actions ALTER COLUMN missing_old SET NOT NULL")
    op.execute("ALTER TABLE pending_actions DROP COLUMN missing")
    op.execute("ALTER TABLE pending_actions RENAME COLUMN missing_old TO missing")

    op.execute("ALTER TABLE events ALTER COLUMN source TYPE varchar(7)")
    op.execute("UPDATE events SET source = 'import_' WHERE source = 'import'")
