from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    chatbots: int
    messages_per_month: int


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(chatbots=1, messages_per_month=100),
    "starter": PlanLimits(chatbots=2, messages_per_month=3_000),
    "pro": PlanLimits(chatbots=5, messages_per_month=12_000),
    "agency": PlanLimits(chatbots=25, messages_per_month=50_000),
    "enterprise": PlanLimits(chatbots=-1, messages_per_month=-1),
}


def get_limits(plan: str) -> PlanLimits:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
