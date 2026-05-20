"""Application configuration via environment and Pydantic Settings."""

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _expand_home(value: str) -> Path:
    return Path(value).expanduser().resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Cortex Workbench"
    debug: bool = False
    data_dir: Path = Field(default_factory=lambda: _expand_home("~/.siwz-rag-lite"))
    log_level: str = "INFO"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_batch_size: int = 8

    retrieval_top_k: int = 20
    retrieval_top_n: int = 8

    llm_provider: str = "ollama"  # ollama | anthropic
    ollama_timeout_seconds: float = 300.0
    extraction_max_llm_blocks: int = 30

    @property
    def extraction_use_llm(self) -> bool:
        """Default fast heuristic extraction; enable LLM in Settings or EXTRACTION_USE_LLM=1."""
        if os.environ.get("EXTRACTION_USE_LLM", "").lower() in ("1", "true", "yes"):
            return True
        return bool(load_user_config().get("extraction_use_llm", False))

    @property
    def kb_active_path(self) -> Path:
        return self.data_dir / "kb-active"

    @property
    def kb_staging_path(self) -> Path:
        return self.data_dir / "kb-staging"

    @property
    def kb_previous_path(self) -> Path:
        return self.data_dir / "kb-previous"

    @property
    def logs_path(self) -> Path:
        return self.data_dir / "logs"

    @property
    def user_config_path(self) -> Path:
        return self.data_dir / "user_config.json"


def load_user_config() -> dict:
    settings = Settings()
    path = settings.user_config_path
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_user_config(data: dict) -> None:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.user_config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    get_settings.cache_clear()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_path.mkdir(parents=True, exist_ok=True)
    user = load_user_config()
    if user.get("llm_provider"):
        settings.llm_provider = user["llm_provider"]
    return settings
