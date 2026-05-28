from __future__ import annotations

import logging

from app.db.database import get_db_connection, get_db_path

logger = logging.getLogger(__name__)

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chatbots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        website_url TEXT,
        system_prompt TEXT DEFAULT '',
        accent_color TEXT DEFAULT '#6366f1',
        scraped_content TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
        session_id TEXT DEFAULT '',
        user_message TEXT NOT NULL,
        bot_response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
        name TEXT,
        email TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingest_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE,
        UNIQUE (chatbot_id, chunk_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chunk_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingest_chunk_id INTEGER NOT NULL UNIQUE,
        chatbot_id INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        model TEXT NOT NULL,
        dimension INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ingest_chunk_id) REFERENCES ingest_chunks (id) ON DELETE CASCADE,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id) ON DELETE CASCADE
    )
    """,
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_chatbots_user_id ON chatbots(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_chatbot_id ON conversations(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_leads_chatbot_id ON leads(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_ingest_chunks_chatbot_id ON ingest_chunks(chatbot_id)",
    "CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chatbot_id ON chunk_embeddings(chatbot_id)",
]


def init_db() -> None:
    """Create tables if they do not exist. Safe to call on every application start."""
    conn = get_db_connection()
    try:
        for stmt in DDL_STATEMENTS:
            conn.execute(stmt)

        # Migrations for columns added after initial release
        _column_migrations = [
            ("leads", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("chatbots", "system_prompt", "TEXT DEFAULT ''"),
            ("chatbots", "accent_color", "TEXT DEFAULT '#6366f1'"),
            ("chatbots", "scraped_content", "TEXT DEFAULT ''"),
            ("conversations", "session_id", "TEXT DEFAULT ''"),
            ("leads", "phone", "TEXT"),
        ]
        for table, column, typedef in _column_migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")
            except Exception as migration_err:
                logger.debug(
                    "Migration %s.%s skipped: %s", table, column, migration_err
                )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_session "
            "ON conversations(chatbot_id, session_id)"
        )

        conn.commit()
        logger.info("SQLite schema ensured (%s)", get_db_path())
    except Exception:
        logger.exception("Failed to initialize database schema")
        conn.rollback()
        raise
    finally:
        conn.close()
