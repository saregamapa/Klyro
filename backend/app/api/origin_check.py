from __future__ import annotations


def origin_allowed(chatbot_row: dict, origin: str | None) -> bool:
    """
    Return True if:
    - The chatbot has no allowed_origins configured (open), OR
    - The request origin matches one of the configured allowed origins.
    """
    raw = str(chatbot_row.get("allowed_origins") or "").strip()
    if not raw:
        return True
    allowed = [o.strip().rstrip("/").lower() for o in raw.split(",") if o.strip()]
    if not allowed:
        return True
    incoming = (origin or "").rstrip("/").lower()
    return incoming in allowed
