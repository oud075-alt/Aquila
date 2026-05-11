from __future__ import annotations

from abc import abstractmethod

from aquila.core.base import CognitiveLayer
from aquila.primitives.schemas import PrimitiveBar, PrimitiveSnapshot


class PrimitiveMetricsService(CognitiveLayer[PrimitiveBar, PrimitiveSnapshot]):
    @abstractmethod
    def append_bar(self, bar: PrimitiveBar) -> None:  # pragma: no cover
        raise NotImplementedError
