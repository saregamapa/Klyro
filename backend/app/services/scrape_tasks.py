from __future__ import annotations

import logging

from app.db.database import get_db_connection
from app.repositories import chatbot_repo
from app.services.scraper import scrape_website_text

logger = logging.getLogger(__name__)


def scrape_and_update_chatbot(chatbot_id: int, website_url: str) -> None:
    """Background task: scrape homepage text into chatbots.scraped_content."""
    try:
        text = scrape_website_text(website_url)
    except ValueError:
        logger.warning(
            "Background scrape skipped chatbot_id=%s url=%s", chatbot_id, website_url
        )
        return
    except Exception:
        logger.exception("Background scrape failed chatbot_id=%s", chatbot_id)
        return

    conn = get_db_connection()
    try:
        chatbot_repo.update_scraped_content(conn, chatbot_id, text)
        conn.commit()
        logger.info("Scraped content saved chatbot_id=%s len=%s", chatbot_id, len(text))
    finally:
        conn.close()
