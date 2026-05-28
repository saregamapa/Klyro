from __future__ import annotations

import hashlib
import logging
import secrets
import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbConn
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.database import db_execute, is_integrity_error
from app.repositories import billing_repo, token_repo, user_repo
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
)
from app.services.email import send_password_reset, send_welcome

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_REFRESH_DAYS = 7


def _refresh_expiry_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=_REFRESH_DAYS)).isoformat()


def _store_refresh(db: DbConn, user_id: int, refresh_token: str) -> None:
    token_repo.store_refresh_token(db, user_id, refresh_token, _refresh_expiry_iso())


@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(request: Request, body: SignupRequest, db: DbConn) -> dict:
    password_hash = hash_password(body.password)
    try:
        new_id = user_repo.create_user(db, body.email, password_hash)
        billing_repo.ensure_free_subscription(db, new_id)
    except Exception as e:
        if not is_integrity_error(e):
            raise
        logger.info("Signup conflict for email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    threading.Thread(target=send_welcome, args=(body.email,), daemon=True).start()
    return {"id": new_id, "email": body.email}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: DbConn) -> TokenResponse:
    user = user_repo.get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    billing_repo.ensure_free_subscription(db, user["id"])
    access_token = create_access_token(user_id=user["id"], email=user["email"])
    refresh_token = create_refresh_token(user_id=user["id"], email=user["email"])
    _store_refresh(db, user["id"], refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: DbConn) -> TokenResponse:
    """
    Exchange a refresh token for a new access token and refresh token.
    Validates that the refresh token is valid and the user still exists.
    """
    if not token_repo.is_refresh_token_valid(db, body.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired",
        )

    try:
        payload = decode_refresh_token(body.refresh_token)
    except Exception as e:
        logger.info("Invalid refresh token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from e

    user_id = int(payload.get("sub", 0))
    user = user_repo.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    token_repo.revoke_refresh_token(db, body.refresh_token)
    new_access_token = create_access_token(user_id=user["id"], email=user["email"])
    new_refresh_token = create_refresh_token(user_id=user["id"], email=user["email"])
    _store_refresh(db, user["id"], new_refresh_token)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest, current_user: CurrentUser, db: DbConn) -> None:
    """Revoke the supplied refresh token. Access token expires naturally (short-lived)."""
    if body.refresh_token:
        token_repo.revoke_refresh_token(db, body.refresh_token)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: DbConn) -> None:
    """Always returns 204 (no user enumeration)."""
    user = user_repo.get_user_by_email(db, body.email)
    if user is None:
        return

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

    db_execute(
        db,
        """
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (token_hash) DO NOTHING
        """,
        (user["id"], token_hash, expires_at),
    )
    reset_url = f"{settings.app_base_url}/reset-password?token={raw_token}"
    send_password_reset(body.email, reset_url)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: DbConn) -> None:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    cur = db_execute(
        db,
        """
        SELECT id, user_id FROM password_reset_tokens
        WHERE token_hash = %s
          AND used_at IS NULL
          AND expires_at > NOW()
        """,
        (token_hash,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    new_hash = hash_password(body.new_password)
    db_execute(
        db,
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (new_hash, row["user_id"]),
    )
    db_execute(
        db,
        "UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s",
        (row["id"],),
    )
    token_repo.revoke_all_user_tokens(db, row["user_id"])
