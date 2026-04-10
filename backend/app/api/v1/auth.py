from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbConn
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import user_repo
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DbConn) -> dict:
    password_hash = hash_password(body.password)
    try:
        new_id = user_repo.create_user(db, body.email, password_hash)
    except sqlite3.IntegrityError:
        logger.info("Signup conflict for email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    return {"id": new_id, "email": body.email}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbConn) -> TokenResponse:
    user = user_repo.get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(user_id=user["id"], email=user["email"])
    return TokenResponse(access_token=token)
