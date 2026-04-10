from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    """Optional override URL; otherwise the chatbot's stored website_url is used."""

    url: Optional[HttpUrl] = Field(
        None,
        description="Seed URL to crawl (must match chatbot domain when overriding)",
    )


class IngestResponse(BaseModel):
    pages_crawled: int
    chunks_stored: int
    urls: list[str] = Field(description="Canonical pages that returned HTML text")


class IngestFilesResponse(BaseModel):
    files_processed: int
    chunks_stored: int
    sources: list[str] = Field(description="Logical source labels, e.g. upload:filename.pdf")
    warnings: list[str] = Field(default_factory=list)
