"""Central registry for anomaly detectors."""

from __future__ import annotations

from typing import Callable

from aquila.core.base import LayerContext
from aquila.detectors.schemas import AnomalyDefinition
from aquila.primitives.schemas import PrimitiveSnapshot


TriggerFn = Callable[[PrimitiveSnapshot, LayerContext], bool]


class DetectorRegistry:
    """Versioned registry. ``(anomaly_id, version)`` is unique."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], tuple[AnomalyDefinition, TriggerFn]] = {}

    def register(self, definition: AnomalyDefinition, trigger_fn: TriggerFn) -> None:
        key = (definition.anomaly_id, definition.version)
        if key in self._items:
            raise ValueError(
                f"Detector already registered: {definition.anomaly_id} v{definition.version}"
            )
        self._items[key] = (definition, trigger_fn)

    def get(self, anomaly_id: str, version: str) -> tuple[AnomalyDefinition, TriggerFn]:
        key = (anomaly_id, version)
        if key not in self._items:
            raise KeyError(f"Detector not registered: {anomaly_id} v{version}")
        return self._items[key]

    def all(self) -> list[tuple[AnomalyDefinition, TriggerFn]]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)
