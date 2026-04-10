from __future__ import annotations

import logging
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Body, File, HTTPException, Path, UploadFile, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.core.config import settings
from app.repositories import ingest_repo
from app.schemas.ingest import IngestFilesResponse, IngestRequest, IngestResponse
from app.services.document_extract import SUPPORTED_EXTENSIONS, extract_plain_text, normalize_extension
from app.services.website_ingest import build_chunk_records, chunk_words, crawl_site, same_registrable_domain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["ingest"])


@router.post(
    "/{chatbot_id}/ingest",
    status_code=status.HTTP_200_OK,
    response_model=IngestResponse,
)
def ingest_chatbot_website(
    chatbot_id: Annotated[int, Path(..., ge=1)],
    db: DbConn,
    current_user: CurrentUser,
    body: Annotated[Optional[IngestRequest], Body()] = None,
) -> IngestResponse:
    row = require_owned_chatbot(db, chatbot_id, current_user.id)

    seed: Optional[str] = None
    if body and body.url is not None:
        seed = str(body.url)
    elif row.get("website_url"):
        seed = row["website_url"]

    if not seed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a url in the body or set the chatbot website_url first",
        )

    stored_website = row.get("website_url")
    if body and body.url is not None and stored_website:
        if not same_registrable_domain(stored_website, seed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ingest url must be on the same domain as the chatbot website_url",
            )

    try:
        pages = crawl_site(seed)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    chunk_rows = build_chunk_records(pages)

    ingest_repo.delete_chunks_for_chatbot(db, chatbot_id)
    stored = ingest_repo.insert_chunks(db, chatbot_id, chunk_rows)

    logger.info(
        "Ingest complete chatbot_id=%s pages=%s chunks=%s",
        chatbot_id,
        len(pages),
        stored,
    )

    return IngestResponse(
        pages_crawled=len(pages),
        chunks_stored=stored,
        urls=[p.url for p in pages],
    )


@router.post(
    "/{chatbot_id}/ingest-files",
    status_code=status.HTTP_200_OK,
    response_model=IngestFilesResponse,
)
def ingest_chatbot_files(
    chatbot_id: Annotated[int, Path(..., ge=1)],
    db: DbConn,
    current_user: CurrentUser,
    files: Annotated[list[UploadFile], File(..., description="One or more documents to train on")],
) -> IngestFilesResponse:
    """
    Append chunks from uploaded files to an existing chatbot (does not remove website-ingested chunks).
    Run website ingest first if you use both URL and files in one session.
    """
    require_owned_chatbot(db, chatbot_id, current_user.id)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were uploaded",
        )

    max_n = settings.ingest_max_upload_files
    if len(files) > max_n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files (max {max_n})",
        )

    max_bytes = settings.ingest_max_upload_bytes_per_file
    warnings: list[str] = []
    pairs: list[tuple[str, str]] = []
    sources: list[str] = []
    files_ok = 0

    for uf in files:
        raw_name = uf.filename or "unnamed"
        safe = os.path.basename(raw_name).strip() or "unnamed"
        ext = normalize_extension(safe)
        if ext not in SUPPORTED_EXTENSIONS:
            warnings.append(
                f"{safe}: unsupported type '{ext or 'none'}' — try PDF, Word (.docx), Excel, TXT, HTML, JSON, RTF, or Pages"
            )
            continue

        # Sync endpoint + sync DB: avoid async def here — SQLite connections are thread-local.
        data = uf.file.read(max_bytes + 1)
        if len(data) > max_bytes:
            warnings.append(f"{safe}: file too large (max {max_bytes // (1024 * 1024)} MiB)")
            continue

        try:
            text = extract_plain_text(safe, data)
        except ValueError as e:
            warnings.append(f"{safe}: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            logger.warning("Extract failed %s: %s", safe, e)
            warnings.append(f"{safe}: could not read file")
            continue

        stripped = text.strip()
        if not stripped:
            warnings.append(f"{safe}: no text extracted")
            continue

        source = f"upload:{safe}"
        sources.append(source)
        chunk_list = chunk_words(stripped)
        if not chunk_list:
            warnings.append(f"{safe}: no chunks after splitting")
            continue
        files_ok += 1
        for ch in chunk_list:
            if ch.strip():
                pairs.append((source, ch))

    if not pairs:
        detail = "No text could be extracted from the uploaded files."
        if warnings:
            detail += " " + " ".join(warnings[:5])
            if len(warnings) > 5:
                detail += f" (+{len(warnings) - 5} more)"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    start = ingest_repo.max_chunk_index(db, chatbot_id) + 1
    triples = [(url, start + i, content) for i, (url, content) in enumerate(pairs)]
    stored = ingest_repo.insert_chunks(db, chatbot_id, triples)

    logger.info(
        "Ingest files chatbot_id=%s files_ok=%s chunks=%s warnings=%s",
        chatbot_id,
        files_ok,
        stored,
        len(warnings),
    )

    return IngestFilesResponse(
        files_processed=files_ok,
        chunks_stored=stored,
        sources=sources,
        warnings=warnings,
    )
