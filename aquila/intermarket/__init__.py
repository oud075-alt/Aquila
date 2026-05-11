"""Cross-asset cognitive correlation.

Per-symbol orchestrators publish their `LayerOutput`s to the intermarket
engine, which scores intermarket contradiction, liquidity migration, and
regime contagion across a configured asset basket (BTC, DXY, Gold, Bonds,
Equities, FX).

Scaffolded: minimal in-process engine. Production: replace with a stream
processor over the distributed event bus.
"""

from aquila.intermarket.engine import IntermarketCognition
from aquila.intermarket.schemas import IntermarketReport, IntermarketRelation

__all__ = ["IntermarketCognition", "IntermarketReport", "IntermarketRelation"]
