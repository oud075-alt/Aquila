"""Phase 0C — Pathology primitives (Appendix M + U).

OHLCV-only deterministic computation. Every primitive returns a bounded
score in [0.0, 1.0]; the structural state classifier returns a closed-enum
label. The PathologyEngine composes all six primitives into a single
`PathologyReport`.
"""

from core.pathology.autocorrelation_breakdown import AutocorrelationBreakdown
from core.pathology.continuation_decay import ContinuationDecay
from core.pathology.dispersion_shock import DispersionShock
from core.pathology.entropy_instability import EntropyInstability
from core.pathology.liquidity_imbalance import LiquidityImbalance
from core.pathology.pathology_engine import PathologyEngine
from core.pathology.structural_state_classifier import StructuralStateClassifier
from core.pathology.volatility_disorder import VolatilityDisorder

__all__ = [
    "AutocorrelationBreakdown",
    "ContinuationDecay",
    "DispersionShock",
    "EntropyInstability",
    "LiquidityImbalance",
    "PathologyEngine",
    "StructuralStateClassifier",
    "VolatilityDisorder",
]
