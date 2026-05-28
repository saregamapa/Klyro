from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.plans import get_limits
from app.core.security import decode_access_token
from app.db.database import DbConnection, get_db
from app.repositories import billing_repo, usage_repo, user_repo

DbConn = Annotated[DbConnection, Depends(get_db)]

http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthedUser:
    id: int
    email: str


def get_current_user(
    db: DbConn,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(http_bearer),
    ],
) -> AuthedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = user_repo.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthedUser(id=user["id"], email=user["email"])


def _plan_for_user(db: DbConn, user_id: int) -> str:
    sub = billing_repo.get_subscription(db, user_id)
    if sub is None:
        return "free"
    if sub.get("status") in ("canceled", "unpaid"):
        return "free"
    return str(sub.get("plan", "free"))


def check_chatbot_quota(db: DbConn, current_user: CurrentUser) -> None:
    plan = _plan_for_user(db, current_user.id)
    limits = get_limits(plan)
    if limits.chatbots == -1:
        return
    current_count = usage_repo.get_chatbot_count(db, current_user.id)
    if current_count >= limits.chatbots:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Your {plan} plan allows {limits.chatbots} chatbot(s). "
                "Upgrade at /pricing to add more."
            ),
        )


def check_message_quota(db: DbConn, current_user: CurrentUser) -> None:
    plan = _plan_for_user(db, current_user.id)
    limits = get_limits(plan)
    if limits.messages_per_month == -1:
        return
    used = usage_repo.get_message_count(db, current_user.id)
    if used >= limits.messages_per_month:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly message limit reached ({limits.messages_per_month} on {plan} plan). "
                "Upgrade at /pricing or wait for next billing period."
            ),
        )


def check_owner_message_quota(db: DbConn, owner_id: int) -> None:
    plan = _plan_for_user(db, owner_id)
    limits = get_limits(plan)
    if limits.messages_per_month == -1:
        return
    used = usage_repo.get_message_count(db, owner_id)
    if used >= limits.messages_per_month:
        raise HTTPException(
            status_code=429,
            detail="This chatbot's message quota is exhausted for this month.",
        )


CurrentUser = Annotated[AuthedUser, Depends(get_current_user)]
ChatbotQuotaOk = Annotated[None, Depends(check_chatbot_quota)]
MessageQuotaOk = Annotated[None, Depends(check_message_quota)]

__all__ = [
    "AuthedUser",
    "ChatbotQuotaOk",
    "CurrentUser",
    "DbConn",
    "MessageQuotaOk",
    "check_owner_message_quota",
    "get_current_user",
    "http_bearer",
]
