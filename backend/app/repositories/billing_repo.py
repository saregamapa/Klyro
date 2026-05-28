from __future__ import annotations

import logging
from typing import Any

from app.db.database import db_execute, row_to_dict

logger = logging.getLogger(__name__)


def get_subscription(conn: Any, user_id: int) -> dict[str, Any] | None:
    cur = db_execute(
        conn,
        "SELECT * FROM subscriptions WHERE user_id = %s",
        (user_id,),
    )
    return row_to_dict(cur.fetchone())


def upsert_subscription(
    conn: Any,
    user_id: int,
    *,
    plan: str,
    status: str,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    current_period_end: str | None = None,
    trial_end: str | None = None,
) -> None:
    db_execute(
        conn,
        """
        INSERT INTO subscriptions
            (user_id, plan, status, stripe_customer_id,
             stripe_subscription_id, current_period_end, trial_end, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            plan = EXCLUDED.plan,
            status = EXCLUDED.status,
            stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, subscriptions.stripe_customer_id),
            stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, subscriptions.stripe_subscription_id),
            current_period_end = EXCLUDED.current_period_end,
            trial_end = EXCLUDED.trial_end,
            updated_at = NOW()
        """,
        (
            user_id,
            plan,
            status,
            stripe_customer_id,
            stripe_subscription_id,
            current_period_end,
            trial_end,
        ),
    )
    logger.info("upsert_subscription user_id=%s plan=%s status=%s", user_id, plan, status)


def get_user_by_stripe_customer_id(conn: Any, stripe_customer_id: str) -> dict[str, Any] | None:
    cur = db_execute(
        conn,
        """
        SELECT u.* FROM users u
        JOIN subscriptions s ON s.user_id = u.id
        WHERE s.stripe_customer_id = %s
        """,
        (stripe_customer_id,),
    )
    return row_to_dict(cur.fetchone())


def ensure_free_subscription(conn: Any, user_id: int) -> None:
    db_execute(
        conn,
        """
        INSERT INTO subscriptions (user_id, plan, status)
        VALUES (%s, 'free', 'active')
        ON CONFLICT (user_id) DO NOTHING
        """,
        (user_id,),
    )
