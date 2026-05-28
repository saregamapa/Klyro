from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 2


async def run_worker_loop() -> None:
    """
    Async loop: poll ingest_jobs for pending work every 2 seconds.
    Runs as an asyncio task in the FastAPI lifespan.
    Uses asyncio.to_thread to run sync DB + network calls off the event loop.
    """
    logger.info("Job worker started")
    while True:
        try:
            processed = await asyncio.to_thread(_process_next_job)
            if not processed:
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        except Exception:
            logger.exception("Job worker error")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)


def _process_next_job() -> bool:
    """Claim and run one pending job. Returns True if a job was processed."""
    from app.db.database import get_db_connection
    from app.repositories import job_repo

    conn = get_db_connection()
    try:
        job = job_repo.claim_next_pending(conn)
        conn.commit()
        if job is None:
            return False

        job_id = job["id"]
        job_type = job["job_type"]
        chatbot_id = job["chatbot_id"]
        payload = json.loads(job.get("payload") or "{}")
        logger.info(
            "Worker claimed job_id=%s type=%s chatbot_id=%s",
            job_id,
            job_type,
            chatbot_id,
        )
    finally:
        conn.close()

    try:
        if job_type == "website_ingest":
            result = _run_website_ingest(chatbot_id, payload)
        elif job_type in ("embed", "file_embed"):
            result = _run_embed(chatbot_id)
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        conn2 = get_db_connection()
        try:
            job_repo.mark_done(conn2, job_id, result)
            conn2.commit()
        finally:
            conn2.close()

        logger.info("Job done job_id=%s result=%s", job_id, result)
        return True

    except Exception as exc:
        logger.exception("Job failed job_id=%s", job_id)
        conn3 = get_db_connection()
        try:
            job_repo.mark_error(conn3, job_id, str(exc))
            conn3.commit()
        finally:
            conn3.close()
        return True


def _run_website_ingest(chatbot_id: int, payload: dict) -> dict:
    from app.core.config import settings
    from app.db.database import get_db_connection
    from app.repositories import chatbot_repo, ingest_repo
    from app.services.website_ingest import build_chunk_records, crawl_site, same_registrable_domain

    seed = payload.get("url", "")
    if not seed:
        raise ValueError("No URL in job payload")

    conn = get_db_connection()
    try:
        row = chatbot_repo.get_chatbot_by_id(conn, chatbot_id)
        if row is None:
            raise ValueError("Chatbot not found")
        stored_website = row.get("website_url")
        if stored_website and not same_registrable_domain(stored_website, seed):
            raise ValueError(
                "Ingest url must be on the same domain as the chatbot website_url"
            )
    finally:
        conn.close()

    pages = crawl_site(seed)
    chunk_rows = build_chunk_records(pages)

    conn = get_db_connection()
    try:
        ingest_repo.delete_chunks_for_chatbot(conn, chatbot_id)
        stored = ingest_repo.insert_chunks(conn, chatbot_id, chunk_rows)
        conn.commit()
    finally:
        conn.close()

    embed_result = {}
    if settings.openai_api_key.strip():
        embed_result = _run_embed(chatbot_id)

    return {
        "pages_crawled": len(pages),
        "chunks_stored": stored,
        "urls": [p.url for p in pages],
        **embed_result,
    }


def _run_embed(chatbot_id: int) -> dict:
    from app.core.config import settings
    from app.db.database import get_db_connection
    from app.repositories import embedding_repo
    from app.services.embedding_service import get_embedding_service
    from app.services.vector_store import get_vector_store

    if not settings.openai_api_key.strip():
        return {"embedded": 0, "note": "OPENAI_API_KEY not configured"}

    conn = get_db_connection()
    try:
        chunks = embedding_repo.list_ingest_chunks_for_chatbot(conn, chatbot_id)
        if not chunks:
            return {"embedded": 0, "note": "no chunks"}

        store = get_vector_store()
        embedder = get_embedding_service()
        store.delete_for_chatbot(chatbot_id, conn=conn)
        vectors = embedder.embed_texts([c["content"] for c in chunks])
        dim = len(vectors[0])
        items = [(int(c["id"]), vectors[i]) for i, c in enumerate(chunks)]
        store.upsert(
            chatbot_id,
            items,
            model=settings.openai_embedding_model,
            dimension=dim,
            conn=conn,
        )
        conn.commit()
        return {"embedded": len(chunks), "dimension": dim}
    finally:
        conn.close()
