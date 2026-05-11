from __future__ import annotations

from abc import abstractmethod

from aquila.core.base import CognitiveLayer
from aquila.temporal.schemas import TemporalCognition, TimeframeState


class TemporalReasoningService(CognitiveLayer[list, TemporalCognition]):
    @abstractmethod
    def update_timeframe(self, state: TimeframeState) -> None:  # pragma: no cover
        raise NotImplementedError
