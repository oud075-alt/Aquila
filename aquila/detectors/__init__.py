"""Anomaly detector registry and baselines.

Detectors are first-class objects. Each registered detector consists of
an immutable ``AnomalyDefinition`` (its scientific contract) and a
``trigger_fn`` (the actual decision function on a ``PrimitiveSnapshot``
plus a ``LayerContext``).

Public API:

- ``AnomalyDefinition`` — the contract.
- ``AnomalyScope`` / ``OutcomeRule`` / ``SuccessMetric`` — sub-schemas.
- ``TriggerRecord``   — emitted when a detector fires.
- ``DetectorRegistry`` — central registry.
- ``BaselineDetector`` / ``RandomBarSampler`` — null baselines.
"""

from aquila.detectors.baselines import BaselineDetector, RandomBarSampler
from aquila.detectors.registry import DetectorRegistry
from aquila.detectors.schemas import (
    AnomalyDefinition,
    AnomalyScope,
    OutcomeRule,
    SuccessMetric,
    TriggerRecord,
)

__all__ = [
    "AnomalyDefinition",
    "AnomalyScope",
    "OutcomeRule",
    "SuccessMetric",
    "TriggerRecord",
    "DetectorRegistry",
    "BaselineDetector",
    "RandomBarSampler",
]
