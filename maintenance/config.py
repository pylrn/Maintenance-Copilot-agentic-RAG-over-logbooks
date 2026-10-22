"""Server-only settings; no public endpoint serializes this object."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    app_origin: str = "http://localhost:8000"
    additional_app_origins: list[str] = Field(default_factory=list)
    port: int = 8000
    database_url: SecretStr | None = None
    database_schema: str = "public"
    vector_schema: str = "public"
    database_ssl_root_cert: Path | None = None
    statement_cache_size: int = 100
    session_signing_secret: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: Literal["https://api.deepseek.com"] = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    gemini_api_key: SecretStr | None = None
    gemini_base_url: Literal[
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    ] = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_provider: Literal["auto", "deepseek", "gemini"] = "auto"
    model_allowlist: list[str] = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-2.5-flash",
        "deepseek-flash",
        "extractive/v1",
    ]
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
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: Literal["https://jp.cloud.langfuse.com"] = "https://jp.cloud.langfuse.com"
    langfuse_environment: str = "development"
    langfuse_project_id: str = ""

    db_pool_min: int = Field(default=2, ge=1, le=5)
    db_pool_max: int = Field(default=5, ge=1, le=10)
    max_upload_bytes: int = 5 * 1024 * 1024
    max_extracted_chars: int = 50000
    synthesis_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "low"
    synthesis_timeout_seconds: float = Field(default=12.0, ge=1, le=30)
    synthesis_max_tokens: int = Field(default=3072, ge=256, le=8192)
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
        if self.gemini_model not in self.model_allowlist:
            raise ValueError("model not in allowlist")
        if self.rerank_enabled and not self.rerank_revision:
            raise ValueError("reranker revision required")
        if self.app_env == "production":
            for key in ["database_url", "session_signing_secret"]:
                value = getattr(self, key)
                if (
                    not value
                    or not value.get_secret_value()
                    or "REPLACE" in value.get_secret_value()
                ):
                    raise ValueError(f"{key} must be configured")
            has_deepseek = bool(
                self.deepseek_api_key
                and self.deepseek_api_key.get_secret_value()
                and "REPLACE" not in self.deepseek_api_key.get_secret_value()
            )
            has_gemini = bool(
                self.gemini_api_key
                and self.gemini_api_key.get_secret_value()
                and "REPLACE" not in self.gemini_api_key.get_secret_value()
            )
            if self.llm_provider == "deepseek" and not has_deepseek:
                raise ValueError("deepseek_api_key must be configured for deepseek provider")
            if self.llm_provider == "gemini" and not has_gemini:
                raise ValueError("gemini_api_key must be configured for gemini provider")
            if self.llm_provider == "auto" and not (has_deepseek or has_gemini):
                raise ValueError("deepseek_api_key or gemini_api_key must be configured")
            if len(self.session_signing_secret.get_secret_value()) < 32:
                raise ValueError("signing secret too short")
            if not self.app_origin.startswith("https://") or not self.embedding_revision:
                raise ValueError("production needs HTTPS and pinned embeddings")
        return self
