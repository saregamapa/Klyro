from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def _l2_normalize_vector(vec: list[float]) -> list[float]:
    arr = np.asarray(vec, dtype=np.float64)
    n = float(np.linalg.norm(arr))
    if n == 0:
        return vec
    return (arr / n).astype(np.float32).tolist()


class EmbeddingService:
    """OpenAI text embeddings with L2-normalized outputs for cosine similarity via dot product."""

    def __init__(self) -> None:
        self._model = settings.openai_embedding_model

    def _client(self) -> OpenAI:
        if not settings.openai_api_key.strip():
            raise RuntimeError("OPENAI_API_KEY is not configured")
        return OpenAI(api_key=settings.openai_api_key)

    def embed_texts(self, texts: Sequence[str], batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        client = self._client()
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            logger.debug("OpenAI embed batch start=%s size=%s", i, len(batch))
            resp = client.embeddings.create(model=self._model, input=batch)
            # Preserve input order
            by_index = sorted(resp.data, key=lambda d: d.index)
            for item in by_index:
                out.append(_l2_normalize_vector(list(item.embedding)))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
