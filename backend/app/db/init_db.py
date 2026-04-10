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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id INTEGER NOT NULL,
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
]


def init_db() -> None:
    """Create tables if they do not exist. Safe to call on every application start."""
    conn = get_db_connection()
    try:
        for stmt in DDL_STATEMENTS:
            conn.execute(stmt)
        conn.commit()
        logger.info("SQLite schema ensured (%s)", get_db_path())
    except Exception:
        logger.exception("Failed to initialize database schema")
        conn.rollback()
        raise
    finally:
        conn.close()
