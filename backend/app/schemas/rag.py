from pydantic import BaseModel, Field


class EmbedResponse(BaseModel):
    chunks_embedded: int
    model: str
    vector_backend: str
    embedding_dimension: int


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    top_k: int = Field(5, ge=1, le=50)


class RetrieveHit(BaseModel):
    ingest_chunk_id: int
    score: float
    content: str
    source_url: str
    chunk_index: int


class RetrieveResponse(BaseModel):
    results: list[RetrieveHit]
