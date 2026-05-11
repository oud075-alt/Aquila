from __future__ import annotations

from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.regime.interfaces import RegimeDetector
from aquila.regime.schemas import RegimeKind


class ParticipationRegimeDetector(RegimeDetector):
    def detect(self, *, primitives: PrimitiveSnapshot, structural=None) -> RegimeKind:
        if primitives is None:
            return RegimeKind.HIGH_PARTICIPATION
        if primitives.volume_z < -0.5:
            return RegimeKind.LOW_PARTICIPATION
        return RegimeKind.HIGH_PARTICIPATION
