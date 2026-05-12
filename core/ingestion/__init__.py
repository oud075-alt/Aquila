"""Phase 0B — Ingestion substrate.

Adapters expose a uniform async iterator interface yielding `MarketBar` events.
The default deterministic path is `ReplayAdapter` over Parquet (Appendix S).

LIVE mode (websocket + REST) is provided but is NOT the validation substrate.
"""

from core.ingestion.base_adapter import BaseAdapter, IngestionEvent
from core.ingestion.live_market_adapter import LiveMarketAdapter
from core.ingestion.ohlcv_pipeline import OHLCVPipeline
from core.ingestion.replay_adapter import ReplayAdapter
from core.ingestion.tick_pipeline import Tick, TickPipeline
from core.ingestion.websocket_manager import WebsocketManager

__all__ = [
    "BaseAdapter",
    "IngestionEvent",
    "LiveMarketAdapter",
    "OHLCVPipeline",
    "ReplayAdapter",
    "Tick",
    "TickPipeline",
    "WebsocketManager",
]
