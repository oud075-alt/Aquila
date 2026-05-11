"""Layer 0 — Real-time / replay-safe market ingestion.

Closes audit gap #2 (no data ingestion) and matches the expansion's
real-time ingestion architecture section.

Sub-modules:
- schemas.py     : RawEvent, OHLCV, OrderFlowEvent, MacroEvent
- interfaces.py  : MarketDataAdapter, IngestionGateway
- adapters.py    : InProcAdapter, ReplayAdapter
- normalize.py   : timestamp normalization + dedup
- instruments.py : asset/instrument master
- trust.py       : per-source trust scoring
- audit.py       : ingestion audit log
"""

from aquila.ingestion.adapters import InProcAdapter, ReplayAdapter
from aquila.ingestion.instruments import Instrument, InstrumentMaster
from aquila.ingestion.interfaces import IngestionGateway, MarketDataAdapter
from aquila.ingestion.normalize import IngestionNormalizer
from aquila.ingestion.schemas import (
    MacroEvent,
    OHLCV,
    OrderFlowEvent,
    RawEvent,
    RawEventKind,
)
from aquila.ingestion.trust import SourceTrustRegistry

__all__ = [
    "InProcAdapter",
    "ReplayAdapter",
    "Instrument",
    "InstrumentMaster",
    "IngestionGateway",
    "MarketDataAdapter",
    "IngestionNormalizer",
    "MacroEvent",
    "OHLCV",
    "OrderFlowEvent",
    "RawEvent",
    "RawEventKind",
    "SourceTrustRegistry",
]
