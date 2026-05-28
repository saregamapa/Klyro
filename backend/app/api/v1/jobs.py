from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, status

from app.api.deps import CurrentUser, DbConn
from app.db.database import db_execute, row_to_dict
from app.repositories import job_repo

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse_json_field(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


@router.get("/{job_id}")
def get_job_status(
    job_id: Annotated[int, Path(..., ge=1)],
    db: DbConn,
    current_user: CurrentUser,
) -> dict:
    job = job_repo.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    cur = db_execute(db, "SELECT user_id FROM chatbots WHERE id = %s", (job["chatbot_id"],))
    bot = row_to_dict(cur.fetchone())
    if not bot or bot["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return {
        "job_id": job["id"],
        "chatbot_id": job["chatbot_id"],
        "type": job["job_type"],
        "status": job["status"],
        "result": _parse_json_field(job.get("result")),
        "error": job.get("error"),
        "created_at": str(job["created_at"]),
        "started_at": str(job["started_at"]) if job.get("started_at") else None,
        "finished_at": str(job["finished_at"]) if job.get("finished_at") else None,
    }
