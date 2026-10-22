"""Server-only settings; no public endpoint serializes this object."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    app_origin: str = "http://localhost:8000"
    port: int = 8000
    database_url: SecretStr | None = None
    session_signing_secret: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: Literal["https://api.deepseek.com"] = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    model_allowlist: list[str] = ["deepseek-flash"]
    embedding_model: Literal["BAAI/bge-small-en-v1.5"] = "BAAI/bge-small-en-v1.5"
    embedding_dim: Literal[384] = 384
    embedding_revision: str = ""
    embedding_query_prefix: str = "Represent this sentence for searching relevant passages: "
    model_cache_dir: Path = Path("models")
    artifact_dir: Path = Path("artifacts")
    rerank_enabled: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    rerank_revision: str = ""
    langfuse_enabled: bool = False
    db_pool_min: int = Field(default=2, ge=1, le=5)
    db_pool_max: int = Field(default=5, ge=1, le=10)
    max_upload_bytes: int = 5 * 1024 * 1024
    max_extracted_chars: int = 50000
    run_deadline_seconds: int = 45
    max_tool_calls: int = 8
    max_model_requests: int = 4
    max_search_calls: int = 3
    cpu_concurrency: int = 1
    owner_cookie_max_age: int = 86400 * 30

    @model_validator(mode="after")
    def secure_production(self):
        if self.db_pool_min > self.db_pool_max:
            raise ValueError("invalid pool limits")
        if self.deepseek_model not in self.model_allowlist:
            raise ValueError("model not in allowlist")
        if self.rerank_enabled and not self.rerank_revision:
            raise ValueError("reranker revision required")
        if self.app_env == "production":
            for key in ["database_url", "session_signing_secret", "deepseek_api_key"]:
                value = getattr(self, key)
                if (
                    not value
                    or not value.get_secret_value()
                    or "REPLACE" in value.get_secret_value()
                ):
                    raise ValueError(f"{key} must be configured")
            if len(self.session_signing_secret.get_secret_value()) < 32:
                raise ValueError("signing secret too short")
            if not self.app_origin.startswith("https://") or not self.embedding_revision:
                raise ValueError("production needs HTTPS and pinned embeddings")
        return self
