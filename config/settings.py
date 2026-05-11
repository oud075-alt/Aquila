"""Global runtime settings loaded from environment / `.env` file.

The configuration is intentionally explicit and strongly typed via pydantic.
Every other module of the MSPIS reads its configuration from here so that
behaviour can be controlled through environment variables without touching
code.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration.

    Values are read from the environment (and an optional ``.env`` file in
    the project root). All paths are expanded to absolute paths on load so
    that the rest of the system can treat them as canonical.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Runtime ----------------------------------------------------------
    env: str = Field(default="production", alias="MSPIS_ENV")
    log_level: str = Field(default="INFO", alias="MSPIS_LOG_LEVEL")
    timezone: str = Field(default="UTC", alias="MSPIS_TIMEZONE")
    data_dir: Path = Field(default=Path("./data"), alias="MSPIS_DATA_DIR")
    memory_dir: Path = Field(default=Path("./data/memory"), alias="MSPIS_MEMORY_DIR")

    # ---- API server -------------------------------------------------------
    api_host: str = Field(default="0.0.0.0", alias="MSPIS_API_HOST")
    api_port: int = Field(default=8080, alias="MSPIS_API_PORT")
    api_workers: int = Field(default=1, alias="MSPIS_API_WORKERS")
    api_key: str | None = Field(default=None, alias="MSPIS_API_KEY")

    # ---- Default universe -------------------------------------------------
    default_exchange: str = Field(default="binance", alias="MSPIS_DEFAULT_EXCHANGE")
    default_symbols_raw: str = Field(
        default="BTC/USDT,ETH/USDT", alias="MSPIS_DEFAULT_SYMBOLS"
    )
    default_timeframes_raw: str = Field(
        default="1m,5m,15m,1h,4h,1d", alias="MSPIS_DEFAULT_TIMEFRAMES"
    )
    history_bars: int = Field(default=1500, alias="MSPIS_HISTORY_BARS")

    # ---- Vector memory ----------------------------------------------------
    chroma_persist_dir: Path = Field(
        default=Path("./data/memory/chroma"), alias="CHROMA_PERSIST_DIR"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

    # ---- Redis (optional) -------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")

    # ---- OpenAI -----------------------------------------------------------
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=1200, alias="OPENAI_MAX_TOKENS")

    # ---- Calendar / News --------------------------------------------------
    econ_calendar_provider: str = Field(
        default="tradingeconomics", alias="ECON_CALENDAR_PROVIDER"
    )
    news_provider: str = Field(default="cryptopanic", alias="NEWS_PROVIDER")

    # ---------------------------------------------------------------------
    # Validators
    # ---------------------------------------------------------------------
    @field_validator("data_dir", "memory_dir", "chroma_persist_dir", mode="after")
    @classmethod
    def _resolve_path(cls, v: Path) -> Path:
        p = Path(v).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @field_validator("log_level", mode="after")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    # ---------------------------------------------------------------------
    # Derived helpers
    # ---------------------------------------------------------------------
    @property
    def default_symbols(self) -> List[str]:
        return [s.strip() for s in self.default_symbols_raw.split(",") if s.strip()]

    @property
    def default_timeframes(self) -> List[str]:
        return [t.strip() for t in self.default_timeframes_raw.split(",") if t.strip()]

    @property
    def logs_dir(self) -> Path:
        p = self.data_dir / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton :class:`Settings` instance."""
    return Settings()  # type: ignore[call-arg]


# Eagerly create data directories when the module is imported so that even
# fresh installations always have the expected layout on disk.
_settings = get_settings()
for _d in (_settings.data_dir, _settings.memory_dir, _settings.logs_dir, _settings.chroma_persist_dir):
    os.makedirs(_d, exist_ok=True)
