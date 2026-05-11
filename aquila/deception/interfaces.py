from __future__ import annotations

from abc import ABC, abstractmethod

from aquila.core.base import CognitiveLayer
from aquila.deception.schemas import DeceptionReport, LureClassification, TrapSignature
from aquila.pathology.schemas import PathologyReport


class TrapDetector(ABC):
    @abstractmethod
    def detect(self, *, structural, pathology, primitives) -> list[TrapSignature]:  # pragma: no cover
        raise NotImplementedError


class LureClassifier(ABC):
    @abstractmethod
    def classify(self, *, structural, pathology, primitives) -> list[LureClassification]:  # pragma: no cover
        raise NotImplementedError


class DeceptionService(CognitiveLayer[PathologyReport, DeceptionReport]):
    pass
