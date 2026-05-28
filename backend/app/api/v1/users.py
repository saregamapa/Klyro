from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, DbConn
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.database import db_execute, row_to_dict, rows_to_dicts
from app.repositories import token_repo, user_repo
from app.schemas.user import ChangePasswordRequest, UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def read_me(current_user: CurrentUser, db: DbConn) -> UserPublic:
    row = user_repo.get_user_by_id(db, current_user.id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return UserPublic(
        id=row["id"],
        email=row["email"],
        created_at=str(row["created_at"]),
    )


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbConn,
) -> None:
    """Change password while authenticated. Revokes all other sessions."""
    row = user_repo.get_user_by_id(db, current_user.id)
    if row is None or not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    new_hash = hash_password(body.new_password)
    db_execute(
        db,
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (new_hash, current_user.id),
    )
    token_repo.revoke_all_user_tokens(db, current_user.id)


@router.get("/me/export")
def export_my_data(current_user: CurrentUser, db: DbConn) -> JSONResponse:
    """GDPR data portability — returns all data associated with this account as JSON."""
    user = row_to_dict(
        db_execute(
            db,
            "SELECT id, email, created_at FROM users WHERE id = %s",
            (current_user.id,),
        ).fetchone()
    )

    sub = row_to_dict(
        db_execute(
            db,
            "SELECT plan, status, current_period_end FROM subscriptions WHERE user_id = %s",
            (current_user.id,),
        ).fetchone()
    )

    chatbots = rows_to_dicts(
        db_execute(
            db,
            "SELECT id, name, website_url, created_at FROM chatbots WHERE user_id = %s",
            (current_user.id,),
        ).fetchall()
    )

    conversations = rows_to_dicts(
        db_execute(
            db,
            """
            SELECT conv.id, conv.chatbot_id, conv.session_id, conv.user_message,
                   conv.bot_response, conv.created_at
            FROM conversations conv
            JOIN chatbots c ON c.id = conv.chatbot_id
            WHERE c.user_id = %s
            ORDER BY conv.created_at DESC
            LIMIT 10000
            """,
            (current_user.id,),
        ).fetchall()
    )

    leads = rows_to_dicts(
        db_execute(
            db,
            """
            SELECT l.id, l.chatbot_id, l.name, l.email, l.message, l.created_at
            FROM leads l
            JOIN chatbots c ON c.id = l.chatbot_id
            WHERE c.user_id = %s
            ORDER BY l.created_at DESC
            LIMIT 10000
            """,
            (current_user.id,),
        ).fetchall()
    )

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {k: str(v) if v else v for k, v in (user or {}).items()},
        "subscription": {k: str(v) if v else v for k, v in (sub or {}).items()},
        "chatbots": [{k: str(v) if v else v for k, v in row.items()} for row in chatbots],
        "conversations": [
            {k: str(v) if v else v for k, v in row.items()} for row in conversations
        ],
        "leads": [{k: str(v) if v else v for k, v in row.items()} for row in leads],
    }

    return JSONResponse(
        content=export,
        headers={"Content-Disposition": "attachment; filename=klyro-export.json"},
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(current_user: CurrentUser, db: DbConn) -> None:
    """
    GDPR right to erasure. Cancels Stripe subscription first, then deletes the user
    row (all chatbots, conversations, leads cascade-delete via FK).
    """
    from app.repositories import billing_repo

    sub = billing_repo.get_subscription(db, current_user.id)
    if sub and sub.get("stripe_subscription_id") and settings.stripe_secret_key:
        try:
            import stripe

            stripe.api_key = settings.stripe_secret_key
            stripe.Subscription.cancel(sub["stripe_subscription_id"])
        except Exception:
            logger.warning(
                "Could not cancel Stripe subscription for user %s",
                current_user.id,
            )

    db_execute(db, "DELETE FROM users WHERE id = %s", (current_user.id,))
    logger.info("Account deleted user_id=%s", current_user.id)
