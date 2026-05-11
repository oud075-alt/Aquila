"""Phase 2 — Multi-timeframe context fusion.

Fuses TimeframeSnapshots from active streams into a TimeframeContext
(Appendix C). Computes alignment, divergence, and macro→local propagation.

Phase 0 single-timeframe runtime supplies one snapshot — the engine remains
useful (returns a self-aligned context with conflict_score = 0) and is ready
to scale up to all 5 mandatory timeframes when the runtime registers them.
"""

from __future__ import annotations

from collections import Counter
from statistics import fmean, pstdev

from core.orchestrator.context_manager import ContextManager
from core.pathology.metrics import clip01
from core.schemas.enums import Regime, Timeframe
from core.schemas.timeframe_context import TimeframeContext, TimeframeSnapshot

DEFENSIVE_REGIMES: frozenset[Regime] = frozenset(
    {Regime.DEFENSIVE, Regime.ENTROPIC, Regime.LIQUIDITY_VACUUM, Regime.EXPANSION_UNSTABLE, Regime.COMPRESSION_UNSTABLE, Regime.TREND_FRAGILE}
)


class ContextFusionEngine:
    """Phase 2 — context fusion across active timeframes."""

    async def fuse(self, manager: ContextManager) -> TimeframeContext | None:
        snaps = manager.all_snapshots()
        if not snaps:
            return None
        return self._fuse(snaps)

    def _fuse(self, snaps: list[TimeframeSnapshot]) -> TimeframeContext:
        snaps_sorted = sorted(snaps, key=lambda s: s.timeframe.order)
        highest = snaps_sorted[-1]
        lowest = snaps_sorted[0]

        regimes = [s.regime for s in snaps_sorted]
        regime_counts = Counter(regimes)
        macro_bias = regime_counts.most_common(1)[0][0]
        local_bias = lowest.regime

        consensus_count = max(regime_counts.values())
        structural_consensus = clip01(consensus_count / len(snaps_sorted))

        instabilities = [s.instability_score for s in snaps_sorted]
        healths = [s.structural_health for s in snaps_sorted]
        mean_inst = fmean(instabilities)
        spread_inst = pstdev(instabilities) if len(instabilities) > 1 else 0.0

        unique_regimes = len(regime_counts)
        regime_conflict = clip01((unique_regimes - 1) / max(len(snaps_sorted) - 1, 1))
        instability_conflict = clip01(spread_inst * 2.0)
        timeframe_conflict_score = clip01(0.5 * regime_conflict + 0.5 * instability_conflict)

        alignment = clip01(1.0 - timeframe_conflict_score)
        macro_inst = max(
            (s.instability_score for s in snaps_sorted if s.timeframe.order >= 2),
            default=mean_inst,
        )
        local_health = max(
            (s.structural_health for s in snaps_sorted if s.timeframe.order <= 1),
            default=fmean(healths),
        )
        escalation_alignment = clip01(macro_inst * (1.0 - local_health))

        reasoning = (
            f"timeframes={[s.timeframe.value for s in snaps_sorted]}",
            f"regimes={[r.value for r in regimes]}",
            f"macro={macro_bias.value}",
            f"local={local_bias.value}",
            f"conflict={timeframe_conflict_score:.2f}",
            f"alignment={alignment:.2f}",
            f"escalation_alignment={escalation_alignment:.2f}",
        )

        confidence = clip01(alignment * (1.0 - mean_inst))

        return TimeframeContext(
            timestamp=highest.timestamp,
            timeframe=highest.timeframe,
            source=highest.source,
            confidence=confidence,
            snapshots=tuple(snaps_sorted),
            context_alignment_score=alignment,
            macro_bias=macro_bias,
            local_bias=local_bias,
            timeframe_conflict_score=timeframe_conflict_score,
            structural_consensus=structural_consensus,
            escalation_alignment=escalation_alignment,
            higher_timeframe_authority=highest.timeframe,
            reasoning=reasoning,
        )
