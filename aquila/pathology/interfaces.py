from __future__ import annotations

from aquila.core.base import CognitiveLayer
from aquila.pathology.schemas import PathologyReport
from aquila.structural.schemas import StructuralDiagnosis


class PathologyService(CognitiveLayer[StructuralDiagnosis, PathologyReport]):
    pass
