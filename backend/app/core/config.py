from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _backend_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _env_files() -> tuple[str, ...]:
    backend = _backend_dir()
    return (str(backend / ".env"), str(backend.parent / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "KlyroAI"
    environment: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    database_url: str = ""
    database_path: str = "database.db"

    frontend_static_dir: str = "../frontend/static"
    frontend_templates_dir: str = "../frontend/templates"

    ingest_max_depth: int = 2
    ingest_max_pages: int = 40
    ingest_request_timeout_seconds: float = 15.0
    ingest_chunk_min_words: int = 500
    ingest_chunk_max_words: int = 1000
    ingest_max_upload_files: int = 30
    ingest_max_upload_bytes_per_file: int = 35 * 1024 * 1024

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    rag_chat_top_k: int = 5

    vector_backend: str = "sqlite"
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""

    cors_allow_origins: str = "*"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_agency: str = ""
    app_base_url: str = "http://localhost:8000"

    @property
    def use_postgres(self) -> bool:
        return bool(self.database_url and self.database_url.startswith("postgresql"))

    @property
    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_allow_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def database_file(self) -> Path:
        p = Path(self.database_path)
        return p if p.is_absolute() else (_backend_dir() / p).resolve()

    @property
    def static_path(self) -> Path:
        p = Path(self.frontend_static_dir)
        return p if p.is_absolute() else (_backend_dir() / p).resolve()

    @property
    def templates_path(self) -> Path:
        p = Path(self.frontend_templates_dir)
        return p if p.is_absolute() else (_backend_dir() / p).resolve()


settings = Settings()
