from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Query, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.repositories import lead_repo
from app.schemas.lead import LeadCreate, LeadCreated, LeadPublic, PaginatedLeads

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["leads"])


@router.get(
    "/{chatbot_id}/leads",
    response_model=PaginatedLeads,
)
def list_leads(
    chatbot_id: int,
    db: DbConn,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> PaginatedLeads:
    try:
        require_owned_chatbot(db, chatbot_id, current_user.id)
        total = lead_repo.count_leads_for_chatbot(db, chatbot_id)
        rows = lead_repo.list_leads_for_chatbot(db, chatbot_id, limit=limit, offset=offset)
        return PaginatedLeads(
            items=[
                LeadPublic(
                    id=int(r["id"]),
                    chatbot_id=int(r["chatbot_id"]),
                    name=r.get("name"),
                    email=r.get("email"),
                    message=r.get("message"),
                )
                for r in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.exception("Leads endpoint error for chatbot_id=%s: %s", chatbot_id, e)
        raise


@router.post(
    "/{chatbot_id}/leads",
    status_code=status.HTTP_201_CREATED,
    response_model=LeadCreated,
)
def create_lead(
    chatbot_id: int,
    body: LeadCreate,
    db: DbConn,
    current_user: CurrentUser,
) -> LeadCreated:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    try:
        new_id = lead_repo.create_lead(
            db,
            chatbot_id,
            body.name,
            body.email,
            body.message,
        )
    except sqlite3.IntegrityError:
        logger.warning("create_lead integrity error chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create lead",
        ) from None
    return LeadCreated(id=new_id)
