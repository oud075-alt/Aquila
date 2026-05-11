from __future__ import annotations

from aquila.physics.schemas import PhysicsReport, TransitionVelocity
from aquila.structural.schemas import StructuralState


class StateTransitionPhysics:
    def __init__(self) -> None:
        self._last_state: StructuralState | None = None
        self._bars_in_state: int = 0
        self._recent_durations: list[int] = []

    def observe(self, state: StructuralState) -> PhysicsReport:
        rationale: list[str] = []
        last_transition: TransitionVelocity | None = None
        if self._last_state is None:
            self._last_state = state
            self._bars_in_state = 1
            return PhysicsReport()
        if state == self._last_state:
            self._bars_in_state += 1
            return PhysicsReport(instability=0.0, rationale=["holding"])

        last_transition = TransitionVelocity(
            from_state=self._last_state.value, to_state=state.value,
            bars_held=self._bars_in_state,
            rate_per_bar=1.0 / max(1, self._bars_in_state),
        )
        self._recent_durations.append(self._bars_in_state)
        if len(self._recent_durations) > 16:
            self._recent_durations = self._recent_durations[-16:]
        self._last_state = state
        self._bars_in_state = 1

        accelerating = (
            len(self._recent_durations) >= 3
            and self._recent_durations[-1] < self._recent_durations[-2] < self._recent_durations[-3]
        )
        collapsing = self._recent_durations[-3:] == [1, 1, 1] if len(self._recent_durations) >= 3 else False
        instab = 0.4 * (1.0 / max(1, last_transition.bars_held))
        if accelerating:
            rationale.append("transition_accelerating"); instab = min(1.0, instab + 0.3)
        if collapsing:
            rationale.append("regime_collapse_dynamics"); instab = min(1.0, instab + 0.4)
        return PhysicsReport(
            last_transition=last_transition,
            instability=instab,
            accelerating=accelerating,
            collapsing=collapsing,
            rationale=rationale or ["normal_transition"],
        )
