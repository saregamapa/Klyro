from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.db.database import db_execute

logger = logging.getLogger(__name__)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def store_refresh_token(
    conn: Any,
    user_id: int,
    token: str,
    expires_at: str,
) -> None:
    db_execute(
        conn,
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (token_hash) DO NOTHING
        """,
        (user_id, _hash(token), expires_at),
    )


def is_refresh_token_valid(conn: Any, token: str) -> bool:
    """Return True if token exists, is not revoked, and is not expired."""
    cur = db_execute(
        conn,
        """
        SELECT id FROM refresh_tokens
        WHERE token_hash = %s
          AND revoked_at IS NULL
          AND expires_at > NOW()
        """,
        (_hash(token),),
    )
    return cur.fetchone() is not None


def revoke_refresh_token(conn: Any, token: str) -> None:
    db_execute(
        conn,
        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s",
        (_hash(token),),
    )


def revoke_all_user_tokens(conn: Any, user_id: int) -> None:
    """Revoke all active refresh tokens for a user (e.g. password change)."""
    db_execute(
        conn,
        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = %s AND revoked_at IS NULL",
        (user_id,),
    )
