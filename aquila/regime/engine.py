"""Layer 7 engine — Regime Mutation."""

from __future__ import annotations

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.numeric import safe_prob
from aquila.core.types import LayerName
from aquila.pathology.schemas import PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.regime.calibration import AdaptiveCalibrator
from aquila.regime.interfaces import RegimeMutationService
from aquila.regime.liquidity import LiquidityRegimeDetector
from aquila.regime.participation import ParticipationRegimeDetector
from aquila.regime.schemas import RegimeMutationReport, RegimeState
from aquila.regime.tracker import ProbabilisticRegimeTracker
from aquila.regime.transition_graph import RegimeTransitionGraph
from aquila.regime.volatility import VolatilityRegimeDetector


class RegimeMutationLayer(RegimeMutationService):
    layer_name = LayerName.REGIME

    def __init__(self) -> None:
        super().__init__()
        self._vol = VolatilityRegimeDetector()
        self._liq = LiquidityRegimeDetector()
        self._part = ParticipationRegimeDetector()
        self._graph = RegimeTransitionGraph()
        self._tracker = ProbabilisticRegimeTracker()
        self._calibrator = AdaptiveCalibrator()
        self._previous: RegimeState | None = None

    def process(
        self, payload: PathologyReport, ctx: LayerContext
    ) -> LayerOutput[RegimeMutationReport]:
        prim_out = ctx.upstream_outputs.get(LayerName.PRIMITIVES)
        snap: PrimitiveSnapshot | None = prim_out.payload if prim_out else None  # type: ignore[assignment]

        if snap is None:
            empty = RegimeMutationReport(current=RegimeState())
            return self.wrap(payload=empty, ctx=ctx, confidence=0.0, visibility="blind")

        self._calibrator.observe(snap.realized_vol)
        self._vol.low = self._calibrator.low
        self._vol.high = self._calibrator.high

        state = RegimeState(
            volatility=self._vol.detect(primitives=snap),
            liquidity=self._liq.detect(primitives=snap),
            participation=self._part.detect(primitives=snap),
            instability=safe_prob(payload.aggregate_contradiction_score),
        )

        transitions = []
        mutations: list[str] = []
        if self._previous is not None:
            self._graph.observe(self._previous, state)
            if self._previous.volatility != state.volatility:
                mutations.append(f"vol:{self._previous.volatility.value}->{state.volatility.value}")
            if self._previous.liquidity != state.liquidity:
                mutations.append(f"liq:{self._previous.liquidity.value}->{state.liquidity.value}")
            if self._previous.participation != state.participation:
                mutations.append(f"part:{self._previous.participation.value}->{state.participation.value}")
            transitions.append(self._graph.explain(self._previous, state))

        self._tracker.observe(state)
        self._previous = state

        # instability rises when novel transition + contradictions present
        novel = 1.0 - (transitions[0].probability if transitions else 0.0)
        instab = safe_prob(0.6 * novel + 0.4 * payload.aggregate_contradiction_score)

        report = RegimeMutationReport(
            current=state,
            mutations=mutations,
            transitions=transitions,
            instability_score=instab,
            calibration_delta=self._calibrator.delta(),
        )
        return self.wrap(payload=report, ctx=ctx, confidence=1.0 - instab, visibility="full")
