from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbConn
from app.repositories import user_repo
from app.schemas.user import UserPublic

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
