"""Live market adapter — websocket OHLCV / kline streaming.

LIVE is the secondary path (Appendix 0B). Production deployments wire this
to the orchestrator; deterministic replay tests do NOT depend on it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from core.ingestion.base_adapter import BaseAdapter, IngestionEvent
from core.ingestion.websocket_manager import WebsocketManager
from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL, MarketBar


class LiveMarketAdapter(BaseAdapter):
    """Generic live kline streamer.

    Expects each websocket payload to expose a kline object compatible with
    Binance-style fields:

        {
            "k": {"t": <open_time_ms>, "o","h","l","c","v": ..., "x": <closed>}
        }

    Other exchanges can be supported by injecting a `payload_mapper`.
    """

    def __init__(
        self,
        ws_url: str,
        *,
        symbol: str = DEFAULT_SYMBOL,
        timeframe: Timeframe = Timeframe.ONE_MIN,
        watermark_tolerance_bars: int = 2,
    ) -> None:
        super().__init__(
            symbol=symbol,
            timeframe=timeframe,
            source=SourceMode.LIVE_WS,
            watermark_tolerance_bars=watermark_tolerance_bars,
        )
        self.ws = WebsocketManager(ws_url)

    @staticmethod
    def _default_map(payload: dict[str, object]) -> dict[str, object] | None:
        k = payload.get("k") if isinstance(payload, dict) else None
        if not isinstance(k, dict):
            return None
        return k

    async def _stream(self) -> AsyncIterator[IngestionEvent]:
        async for message in self.ws.stream():
            k = self._default_map(message.payload)
            if k is None:
                continue
            try:
                event_time = datetime.fromtimestamp(int(str(k["t"])) / 1000.0, tz=UTC)
                bar = MarketBar(
                    timestamp=event_time,
                    timeframe=self.timeframe,
                    source=self.source,
                    confidence=1.0 if bool(k.get("x", False)) else 0.5,
                    symbol=self.symbol,
                    open=float(str(k["o"])),
                    high=float(str(k["h"])),
                    low=float(str(k["l"])),
                    close=float(str(k["c"])),
                    volume=float(str(k["v"])),
                    is_partial=not bool(k.get("x", False)),
                )
            except (KeyError, TypeError, ValueError):
                continue
            yield IngestionEvent(
                bar=bar,
                processing_time=message.received_at,
                event_time=event_time,
                sequence=0,
                is_partial=bar.is_partial,
            )
