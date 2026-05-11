"""Economic calendar feed.

Pulls upcoming macroeconomic events. Multiple providers are supported with
graceful degradation when no credentials are available.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import aiohttp

from brain.logging_utils import get_logger
from config import get_api_keys, get_settings


class EconomicCalendar:
    def __init__(self):
        self.log = get_logger("mspis.sensory.calendar")
        self.settings = get_settings()
        self.keys = get_api_keys()
        self.provider = (self.settings.econ_calendar_provider or "none").lower()
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

    async def upcoming(self, hours: int = 48) -> List[Dict[str, Any]]:
        await self._open()
        try:
            if self.provider == "tradingeconomics":
                return await self._tradingeconomics(hours)
            if self.provider == "financialmodelingprep":
                return await self._fmp(hours)
        except Exception as e:
            self.log.debug("calendar poll error (%s): %s", self.provider, e)
        return []

    async def _tradingeconomics(self, hours: int) -> List[Dict[str, Any]]:
        assert self._session is not None
        token = self.keys.econ_calendar_api_key or "guest:guest"
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=hours)
        d1 = start.date().isoformat()
        d2 = end.date().isoformat()
        url = f"https://api.tradingeconomics.com/calendar/country/all/{d1}/{d2}?c={token}&f=json"
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
        out = []
        for ev in data:
            out.append({
                "country": ev.get("Country"),
                "event": ev.get("Event"),
                "datetime": ev.get("Date"),
                "importance": ev.get("Importance"),
                "actual": ev.get("Actual"),
                "forecast": ev.get("Forecast"),
                "previous": ev.get("Previous"),
            })
        return out

    async def _fmp(self, hours: int) -> List[Dict[str, Any]]:
        assert self._session is not None
        token = self.keys.econ_calendar_api_key
        if not token:
            return []
        start = datetime.now(timezone.utc).date().isoformat()
        end = (datetime.now(timezone.utc) + timedelta(hours=hours)).date().isoformat()
        url = (
            "https://financialmodelingprep.com/api/v3/economic_calendar"
            f"?from={start}&to={end}&apikey={token}"
        )
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
        out = []
        for ev in data:
            out.append({
                "country": ev.get("country"),
                "event": ev.get("event"),
                "datetime": ev.get("date"),
                "importance": ev.get("impact"),
                "actual": ev.get("actual"),
                "forecast": ev.get("estimate"),
                "previous": ev.get("previous"),
            })
        return out
