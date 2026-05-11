from __future__ import annotations

from abc import ABC, abstractmethod

from aquila.core.base import CognitiveLayer
from aquila.pathology.schemas import PathologyReport
from aquila.regime.schemas import RegimeKind, RegimeMutationReport


class RegimeDetector(ABC):
    @abstractmethod
    def detect(self, *, primitives, structural) -> RegimeKind:  # pragma: no cover
        raise NotImplementedError


class RegimeMutationService(CognitiveLayer[PathologyReport, RegimeMutationReport]):
    pass
