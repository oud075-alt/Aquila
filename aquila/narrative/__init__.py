"""Narrative / explainability emitter — analyst-readable, audit-grade.

Outputs structured prose. Strictly no actions, no directions, no prices.
"""

from aquila.narrative.explainer import NarrativeExplainer
from aquila.narrative.schemas import NarrativeReport

__all__ = ["NarrativeExplainer", "NarrativeReport"]
