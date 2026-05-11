"""News stream — pulls recent market news from configurable providers.

Currently supports:

* ``cryptopanic``     — public REST endpoint (auth optional)
* ``finnhub``         — REST endpoint (requires API key)
* ``none``            — disables the feed; ``poll()`` returns empty

The orchestrator embeds the latest news titles in the diagnosis snapshot
so the GPT reasoning layer can correlate structural anomalies with
external catalysts.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

import aiohttp

from brain.logging_utils import get_logger
from config import get_api_keys, get_settings


class NewsStream:
    def __init__(self):
        self.settings = get_settings()
        self.keys = get_api_keys()
        self.log = get_logger("mspis.sensory.news")
        self.provider = (self.settings.news_provider or "none").lower()
        self._session: aiohttp.ClientSession | None = None

    async def _open(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10.0),
                headers={"User-Agent": "MSPIS/1.0"},
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def poll(self, symbols: List[str] | None = None, limit: int = 20) -> List[Dict[str, Any]]:
        await self._open()
        try:
            if self.provider == "cryptopanic":
                return await self._cryptopanic(symbols or [], limit)
            if self.provider == "finnhub":
                return await self._finnhub(symbols or [], limit)
        except Exception as e:
            self.log.debug("news poll error (%s): %s", self.provider, e)
        return []

    async def _cryptopanic(self, symbols: List[str], limit: int) -> List[Dict[str, Any]]:
        assert self._session is not None
        params = {
            "auth_token": self.keys.news_api_key or "",
            "kind": "news",
            "public": "true",
            "regions": "en",
        }
        if symbols:
            params["currencies"] = ",".join(s.split("/")[0] for s in symbols)
        url = "https://cryptopanic.com/api/v1/posts/"
        async with self._session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
        items = data.get("results", [])[:limit]
        return [
            {
                "source": it.get("source", {}).get("title", "cryptopanic"),
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "published": it.get("published_at"),
                "votes": it.get("votes", {}),
            }
            for it in items
        ]

    async def _finnhub(self, symbols: List[str], limit: int) -> List[Dict[str, Any]]:
        assert self._session is not None
        if not self.keys.news_api_key:
            return []
        out: List[Dict[str, Any]] = []
        for sym in symbols[:4] or ["MARKETS"]:
            base = sym.split("/")[0]
            url = (
                "https://finnhub.io/api/v1/company-news"
                f"?symbol={base}&from={datetime.now(timezone.utc).date()}"
                f"&to={datetime.now(timezone.utc).date()}&token={self.keys.news_api_key}"
            )
            try:
                async with self._session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
            except Exception:
                continue
            for it in (data or [])[:limit]:
                out.append({
                    "source": it.get("source", "finnhub"),
                    "title": it.get("headline", ""),
                    "url": it.get("url", ""),
                    "published": it.get("datetime"),
                    "summary": it.get("summary", ""),
                    "symbol": base,
                })
        return out[:limit]
