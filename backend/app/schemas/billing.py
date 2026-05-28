from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

PlanName = Literal["free", "starter", "pro", "agency", "enterprise"]
PlanStatus = Literal["active", "trialing", "past_due", "canceled", "unpaid"]


class CheckoutRequest(BaseModel):
    plan: Literal["starter", "pro", "agency"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionPublic(BaseModel):
    plan: PlanName
    status: PlanStatus
    current_period_end: Optional[str]
    trial_end: Optional[str]
