from __future__ import annotations

import logging

from app.core.config import settings
from app.db.database import db_execute, get_db_connection

logger = logging.getLogger(__name__)

_PG_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    plan                    TEXT NOT NULL DEFAULT 'free'
                            CHECK (plan IN ('free','starter','pro','agency','enterprise')),
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','trialing','past_due','canceled','unpaid')),
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    current_period_end      TIMESTAMPTZ,
    trial_end               TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS message_usage (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period      DATE NOT NULL,
    count       INT NOT NULL DEFAULT 0,
    UNIQUE (user_id, period)
);

CREATE TABLE IF NOT EXISTS chatbots (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    website_url     TEXT,
    system_prompt   TEXT DEFAULT '',
    accent_color    TEXT DEFAULT '#6366f1',
    scraped_content TEXT DEFAULT '',
    allowed_origins TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id              BIGSERIAL PRIMARY KEY,
    chatbot_id      BIGINT NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    session_id      TEXT DEFAULT '',
    user_message    TEXT NOT NULL,
    bot_response    TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
    id          BIGSERIAL PRIMARY KEY,
    chatbot_id  BIGINT NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    name        TEXT,
    email       TEXT,
    phone       TEXT,
    message     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingest_chunks (
    id          BIGSERIAL PRIMARY KEY,
    chatbot_id  BIGINT NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    source_url  TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (chatbot_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id                BIGSERIAL PRIMARY KEY,
    ingest_chunk_id   BIGINT NOT NULL UNIQUE REFERENCES ingest_chunks(id) ON DELETE CASCADE,
    chatbot_id        BIGINT NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    embedding         vector(1536),
    model             TEXT NOT NULL,
    dimension         INT NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chatbots_user_id ON chatbots(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_chatbot_id ON conversations(chatbot_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(chatbot_id, session_id);
CREATE INDEX IF NOT EXISTS idx_leads_chatbot_id ON leads(chatbot_id);
CREATE INDEX IF NOT EXISTS idx_ingest_chunks_chatbot_id ON ingest_chunks(chatbot_id);
CREATE INDEX IF NOT EXISTS idx_chunk_emb_chatbot_id ON chunk_embeddings(chatbot_id);
CREATE INDEX IF NOT EXISTS idx_message_usage_user ON message_usage(user_id, period);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_cust ON subscriptions(stripe_customer_id);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pw_reset_hash ON password_reset_tokens(token_hash);

CREATE TABLE IF NOT EXISTS ingest_jobs (
    id          BIGSERIAL PRIMARY KEY,
    chatbot_id  BIGINT NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    job_type    TEXT NOT NULL DEFAULT 'website',
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','error')),
    payload     JSONB,
    result      JSONB,
    error       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ingest_jobs_status  ON ingest_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_ingest_jobs_chatbot ON ingest_jobs(chatbot_id);
"""

_SQLITE_DDL = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        plan TEXT NOT NULL DEFAULT 'free',
        status TEXT NOT NULL DEFAULT 'active',
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        current_period_end TIMESTAMP,
        trial_end TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS message_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        period TEXT NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,
        UNIQUE (user_id, period)
    )""",
    """CREATE TABLE IF NOT EXISTS chatbots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        website_url TEXT,
        system_prompt TEXT DEFAULT '',
        accent_color TEXT DEFAULT '#6366f1',
        scraped_content TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
        session_id TEXT DEFAULT '',
        user_message TEXT NOT NULL,
        bot_response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
        name TEXT, email TEXT, phone TEXT, message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS ingest_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE,
        UNIQUE (chatbot_id, chunk_index)
    )""",
    """CREATE TABLE IF NOT EXISTS chunk_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingest_chunk_id INTEGER NOT NULL UNIQUE,
        chatbot_id INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        model TEXT NOT NULL,
        dimension INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ingest_chunk_id) REFERENCES ingest_chunks (id) ON DELETE CASCADE,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_chatbots_user_id ON chatbots(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_chatbot_id ON conversations(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(chatbot_id, session_id)",
    "CREATE INDEX IF NOT EXISTS idx_leads_chatbot_id ON leads(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_ingest_chunks_chatbot_id ON ingest_chunks(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_chunk_emb_chatbot_id ON chunk_embeddings(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_message_usage_user ON message_usage(user_id, period)",
    """CREATE TABLE IF NOT EXISTS refresh_tokens (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash  TEXT NOT NULL UNIQUE,
        expires_at  TIMESTAMP NOT NULL,
        revoked_at  TIMESTAMP,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash)",
    """CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash  TEXT NOT NULL UNIQUE,
        expires_at  TIMESTAMP NOT NULL,
        used_at     TIMESTAMP,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS ingest_jobs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id  INTEGER NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
        job_type    TEXT NOT NULL DEFAULT 'website',
        status      TEXT NOT NULL DEFAULT 'pending',
        payload     TEXT,
        result      TEXT,
        error       TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at  TIMESTAMP,
        finished_at TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ingest_jobs_status ON ingest_jobs(status, created_at)",
]


def init_db() -> None:
    conn = get_db_connection()
    try:
        if settings.use_postgres:
            with conn.cursor() as cur:
                cur.execute(_PG_DDL)
        else:
            conn.execute("PRAGMA foreign_keys = ON")
            for stmt in _SQLITE_DDL:
                conn.execute(stmt)
            _sqlite_legacy_migrations(conn)
        conn.commit()
        if settings.use_postgres:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS allowed_origins TEXT DEFAULT ''"
                    )
                conn.commit()
            except Exception as e:
                logger.debug("allowed_origins migration: %s", e)
                conn.rollback()
        backend = "postgres" if settings.use_postgres else "sqlite"
        logger.info("DB schema ensured (backend=%s)", backend)
    except Exception:
        logger.exception("Failed to initialize database schema")
        conn.rollback()
        raise
    finally:
        conn.close()


def _sqlite_legacy_migrations(conn) -> None:
    """Add columns/tables for DBs created before Tier 1."""
    for table, column, typedef in [
        ("leads", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("leads", "phone", "TEXT"),
        ("chatbots", "system_prompt", "TEXT DEFAULT ''"),
        ("chatbots", "accent_color", "TEXT DEFAULT '#6366f1'"),
        ("chatbots", "scraped_content", "TEXT DEFAULT ''"),
        ("conversations", "session_id", "TEXT DEFAULT ''"),
        ("chatbots", "allowed_origins", "TEXT DEFAULT ''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")
        except Exception as err:
            logger.debug("Migration %s.%s skipped: %s", table, column, err)

    for stmt in [
        """CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            plan TEXT NOT NULL DEFAULT 'free',
            status TEXT NOT NULL DEFAULT 'active',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            current_period_end TIMESTAMP,
            trial_end TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS message_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            period TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            UNIQUE (user_id, period)
        )""",
    ]:
        try:
            conn.execute(stmt)
        except Exception as err:
            logger.debug("Legacy table migration skipped: %s", err)
