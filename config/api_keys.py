"""Strongly typed registry for third-party API keys.

We deliberately keep API credentials in a dedicated container so that the
sensory layer can ask for what it needs without spreading ``os.environ``
look-ups across the code base.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIKeys(BaseSettings):
    """Container for every credential that the system may use."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MetaTrader 5 (Windows broker terminal)
    mt5_login: str | None = Field(default=None, alias="MT5_LOGIN")
    mt5_password: str | None = Field(default=None, alias="MT5_PASSWORD")
    mt5_server: str | None = Field(default=None, alias="MT5_SERVER")
    mt5_path: str | None = Field(default=None, alias="MT5_PATH")

    # Binance / CCXT
    binance_api_key: str | None = Field(default=None, alias="BINANCE_API_KEY")
    binance_api_secret: str | None = Field(default=None, alias="BINANCE_API_SECRET")
    binance_use_testnet: bool = Field(default=False, alias="BINANCE_USE_TESTNET")

    # TradingView (unofficial scrape)
    tradingview_username: str | None = Field(default=None, alias="TRADINGVIEW_USERNAME")
    tradingview_password: str | None = Field(default=None, alias="TRADINGVIEW_PASSWORD")

    # Economic calendar
    econ_calendar_api_key: str | None = Field(default=None, alias="ECON_CALENDAR_API_KEY")

    # News stream
    news_api_key: str | None = Field(default=None, alias="NEWS_API_KEY")

    # OpenAI
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    def has_binance(self) -> bool:
        return bool(self.binance_api_key and self.binance_api_secret)

    def has_mt5(self) -> bool:
        return bool(self.mt5_login and self.mt5_password and self.mt5_server)


@lru_cache(maxsize=1)
def get_api_keys() -> APIKeys:
    return APIKeys()  # type: ignore[call-arg]
