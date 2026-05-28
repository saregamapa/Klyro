from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbConn
from app.core.config import settings
from app.core.plans import get_limits
from app.repositories import billing_repo, usage_repo, user_repo
from app.schemas.billing import CheckoutRequest, CheckoutResponse, SubscriptionPublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

_PLAN_TO_PRICE: dict[str, str] = {}


def _price_map() -> dict[str, str]:
    global _PLAN_TO_PRICE
    if not _PLAN_TO_PRICE:
        _PLAN_TO_PRICE = {
            "starter": settings.stripe_price_starter,
            "pro": settings.stripe_price_pro,
            "agency": settings.stripe_price_agency,
        }
    return _PLAN_TO_PRICE


def _ts(unix: int | None) -> str | None:
    if unix is None:
        return None
    return datetime.fromtimestamp(unix, tz=timezone.utc).isoformat()


def _price_to_plan(sub: dict) -> str:
    items = sub.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else ""
    reverse = {v: k for k, v in _price_map().items() if v}
    return reverse.get(price_id, "starter")


@router.get("/subscription", response_model=SubscriptionPublic)
def get_my_subscription(current_user: CurrentUser, db: DbConn) -> SubscriptionPublic:
    row = billing_repo.get_subscription(db, current_user.id)
    if row is None:
        return SubscriptionPublic(
            plan="free", status="active", current_period_end=None, trial_end=None
        )
    return SubscriptionPublic(
        plan=row["plan"],
        status=row["status"],
        current_period_end=str(row["current_period_end"])
        if row.get("current_period_end")
        else None,
        trial_end=str(row["trial_end"]) if row.get("trial_end") else None,
    )


@router.get("/usage")
def get_usage(current_user: CurrentUser, db: DbConn) -> dict:
    sub = billing_repo.get_subscription(db, current_user.id)
    plan = sub.get("plan", "free") if sub else "free"
    limits = get_limits(plan)
    used = usage_repo.get_message_count(db, current_user.id)
    chatbot_count = usage_repo.get_chatbot_count(db, current_user.id)
    pct = (
        round(used / limits.messages_per_month * 100, 1)
        if limits.messages_per_month > 0
        else 0
    )
    return {
        "plan": plan,
        "messages_used": used,
        "messages_limit": limits.messages_per_month,
        "chatbots_used": chatbot_count,
        "chatbots_limit": limits.chatbots,
        "pct_messages": pct,
    }


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    body: CheckoutRequest,
    current_user: CurrentUser,
    db: DbConn,
) -> CheckoutResponse:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    stripe.api_key = settings.stripe_secret_key
    price_id = _price_map().get(body.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    user = user_repo.get_user_by_id(db, current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = billing_repo.get_subscription(db, current_user.id)
    customer_id: str | None = existing.get("stripe_customer_id") if existing else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            metadata={"klyro_user_id": str(current_user.id)},
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        subscription_data={"trial_period_days": 7},
        success_url=f"{settings.app_base_url}/dashboard?upgrade=success",
        cancel_url=f"{settings.app_base_url}/pricing?upgrade=canceled",
        metadata={"klyro_user_id": str(current_user.id), "plan": body.plan},
    )
    return CheckoutResponse(checkout_url=session.url or "")


@router.post("/portal")
def create_customer_portal(current_user: CurrentUser, db: DbConn) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    stripe.api_key = settings.stripe_secret_key
    existing = billing_repo.get_subscription(db, current_user.id)
    if not existing or not existing.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No active subscription found")

    portal = stripe.billing_portal.Session.create(
        customer=existing["stripe_customer_id"],
        return_url=f"{settings.app_base_url}/dashboard",
    )
    return {"portal_url": portal.url}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: DbConn) -> dict:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature") from None

    _handle_stripe_event(db, event)
    return {"received": True}


def _handle_stripe_event(db: Any, event: stripe.Event) -> None:
    etype = event["type"]
    obj = event["data"]["object"]
    logger.info("Stripe event: %s", etype)

    if etype == "checkout.session.completed":
        _on_checkout_complete(db, obj)
    elif etype in ("customer.subscription.updated", "invoice.paid"):
        _on_subscription_updated(
            db,
            obj if etype != "invoice.paid" else None,
            invoice=obj if etype == "invoice.paid" else None,
        )
    elif etype == "customer.subscription.deleted":
        _on_subscription_canceled(db, obj)
    elif etype == "invoice.payment_failed":
        _on_payment_failed(db, obj)


def _on_checkout_complete(db: Any, session: dict) -> None:
    user_id_str = (session.get("metadata") or {}).get("klyro_user_id")
    plan = (session.get("metadata") or {}).get("plan", "starter")
    if not user_id_str:
        return

    stripe.api_key = settings.stripe_secret_key
    sub = stripe.Subscription.retrieve(session["subscription"])
    billing_repo.upsert_subscription(
        db,
        user_id=int(user_id_str),
        plan=plan,
        status=sub["status"],
        stripe_customer_id=session["customer"],
        stripe_subscription_id=sub["id"],
        current_period_end=_ts(sub["current_period_end"]),
        trial_end=_ts(sub.get("trial_end")),
    )


def _on_subscription_updated(
    db: Any, sub: dict | None, invoice: dict | None = None
) -> None:
    stripe.api_key = settings.stripe_secret_key
    if invoice:
        sub_id = invoice.get("subscription")
        if not sub_id:
            return
        sub = stripe.Subscription.retrieve(sub_id)
    if sub is None:
        return

    customer_id = sub["customer"]
    user = billing_repo.get_user_by_stripe_customer_id(db, customer_id)
    if not user:
        return

    billing_repo.upsert_subscription(
        db,
        user_id=user["id"],
        plan=_price_to_plan(sub),
        status=sub["status"],
        stripe_subscription_id=sub["id"],
        current_period_end=_ts(sub["current_period_end"]),
        trial_end=_ts(sub.get("trial_end")),
    )


def _on_subscription_canceled(db: Any, sub: dict) -> None:
    customer_id = sub["customer"]
    user = billing_repo.get_user_by_stripe_customer_id(db, customer_id)
    if user:
        billing_repo.upsert_subscription(
            db, user_id=user["id"], plan="free", status="canceled"
        )


def _on_payment_failed(db: Any, invoice: dict) -> None:
    stripe.api_key = settings.stripe_secret_key
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    sub = stripe.Subscription.retrieve(sub_id)
    user = billing_repo.get_user_by_stripe_customer_id(db, sub["customer"])
    if user:
        billing_repo.upsert_subscription(
            db,
            user_id=user["id"],
            plan=_price_to_plan(sub),
            status="past_due",
        )
