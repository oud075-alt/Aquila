"""Sensory layer — market data ingestion.

Every concrete data source implements :class:`DataFeed` so that the
orchestrator can swap them at runtime without changing downstream code.
"""

from .base import DataFeed, FeedError
from .mt5_feed import MT5Feed
from .binance_feed import BinanceFeed
from .tradingview_feed import TradingViewFeed
from .tick_stream import TickStream
from .candle_stream import CandleStream
from .orderflow_parser import OrderflowParser
from .liquidity_map import LiquidityMap
from .volatility_tracker import VolatilityTracker
from .news_stream import NewsStream
from .economic_calendar import EconomicCalendar

__all__ = [
    "DataFeed",
    "FeedError",
    "MT5Feed",
    "BinanceFeed",
    "TradingViewFeed",
    "TickStream",
    "CandleStream",
    "OrderflowParser",
    "LiquidityMap",
    "VolatilityTracker",
    "NewsStream",
    "EconomicCalendar",
]
