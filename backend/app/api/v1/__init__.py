from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    billing,
    chat,
    chat_proxy,
    chatbots,
    conversations,
    health,
    ingest,
    leads,
    rag,
    users,
    widget_embed,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(billing.router)
router.include_router(users.router)
router.include_router(analytics.router)
router.include_router(chat.router)
router.include_router(chatbots.router)
router.include_router(chat_proxy.router)
router.include_router(ingest.router)
router.include_router(rag.router)
router.include_router(conversations.router)
router.include_router(leads.router)
router.include_router(widget_embed.router)
