"""Schemas for anomaly definitions and detector outputs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import LayerName, Symbol


class AnomalyScope(BaseModel):
    """Where a detector is allowed to fire."""

    model_config = ConfigDict(frozen=True)

    symbols: list[str] = Field(default_factory=lambda: ["*"])
    timeframes: list[str] = Field(default_factory=lambda: ["M5", "M15", "H1"])


class OutcomeRule(BaseModel):
    """How the success of a trigger is measured.

    ``success_expression`` is evaluated by the backtest harness in a
    very restricted namespace containing only the ``ForwardOutcome``
    fields. Detectors must not depend on its evaluator.
    """

    model_config = ConfigDict(frozen=True)

    horizon_bars: int
    success_expression: str


class SuccessMetric(BaseModel):
    """Acceptance criterion declared up-front, not after the fact."""

    model_config = ConfigDict(frozen=True)

    metric: str = "precision"
    threshold: float = 0.55
    baseline: str = "random_bar_sampler"
    significance: str = "bootstrap_p<0.05"


class AnomalyDefinition(BaseModel):
    """First-class contract for a single anomaly."""

    model_config = ConfigDict(frozen=True)

    anomaly_id: str
    version: str
    name: str
    description: str = ""
    scope: AnomalyScope = Field(default_factory=AnomalyScope)
    inputs_required: list[LayerName] = Field(
        default_factory=lambda: [LayerName.PRIMITIVES]
    )
    trigger_rule_ref: str = ""
    outcome_rule: OutcomeRule
    success_metric: SuccessMetric = Field(default_factory=SuccessMetric)
    schema_version: str = "1.0.0"


class TriggerRecord(BaseModel):
    """A single firing of a detector at a single timestamp."""

    model_config = ConfigDict(frozen=True)

    trigger_event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Symbol
    timestamp: datetime
    features: dict[str, float] = Field(default_factory=dict)
    anomaly_id: str
    anomaly_version: str
    range_at_trigger: float = 0.0
