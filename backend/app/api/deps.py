from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

import jwt
import sqlite3
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.db.database import get_db
from app.repositories import user_repo

DbConn = Annotated[sqlite3.Connection, Depends(get_db)]

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


CurrentUser = Annotated[AuthedUser, Depends(get_current_user)]

__all__ = ["AuthedUser", "CurrentUser", "DbConn", "get_current_user", "http_bearer"]
