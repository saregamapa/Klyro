from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import DbConn
from app.core.rate_limit import limiter
from app.db.database import is_integrity_error
from app.repositories import billing_repo, user_repo
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


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
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: DbConn) -> TokenResponse:
    """
    Exchange a refresh token for a new access token and refresh token.
    Validates that the refresh token is valid and the user still exists.
    """
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

    new_access_token = create_access_token(user_id=user["id"], email=user["email"])
    new_refresh_token = create_refresh_token(user_id=user["id"], email=user["email"])
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)
