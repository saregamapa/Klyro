from __future__ import annotations


def user_facing_openai_error(exc: Exception) -> str:
    """Map OpenAI SDK errors to actionable messages for the UI."""
    try:
        from openai import APIConnectionError, AuthenticationError, RateLimitError
    except ImportError:
        return "Embedding provider request failed"

    if isinstance(exc, AuthenticationError):
        return (
            "Invalid OpenAI API key. Set OPENAI_API_KEY in your .env file "
            "(see .env.example) and restart the server."
        )

    if isinstance(exc, APIConnectionError):
        return "Could not reach OpenAI. Check your internet connection and try again."

    if isinstance(exc, RateLimitError):
        code = _error_code(exc)
        if code == "insufficient_quota":
            return (
                "OpenAI quota exceeded. Add billing or credits at "
                "https://platform.openai.com/account/billing then try training again."
            )
        return "OpenAI rate limit hit. Wait a minute and try again."

    # Other APIStatusError subclasses (BadRequestError, etc.)
    name = type(exc).__name__
    if name.endswith("Error") and hasattr(exc, "message"):
        msg = str(getattr(exc, "message", "") or str(exc))
        if msg and len(msg) < 300:
            return msg

    return "Embedding provider request failed"


def _error_code(exc: Exception) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("code") or "")
    return ""
