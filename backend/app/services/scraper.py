from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_CHARS = 4000
_HEADERS = {
    "User-Agent": "KlyroAI-Scraper/1.0",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_website_text(url: str) -> str:
    """
    Fetch a single page and return visible text (capped at 4000 chars).
    Used for lightweight chatbot context when full ingest has not run.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must be http or https with a valid host")

    timeout = settings.ingest_request_timeout_seconds
    try:
        resp = requests.get(url.strip(), headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("scrape_website_text failed url=%s: %s", url, e)
        raise ValueError(f"Could not fetch URL: {e}") from e

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS].rsplit("\n", 1)[0] + "\n…"
    return text
