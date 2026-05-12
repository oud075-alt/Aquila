"""Contradiction matrix loader + evaluator (Appendix N + W + X).

The matrix is data-driven via `rules.yaml`. The loader caches parsed rules
and exposes a deterministic `.evaluate(context)` returning ordered findings.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from core.schemas.enums import ContradictionPolicy

DEFAULT_RULES_PATH: Path = Path(__file__).with_name("rules.yaml")

Op = Literal[">=", "<=", ">", "<", "==", "!="]

_OPS: dict[str, Callable[[float, float], bool]] = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass(frozen=True, slots=True)
class _Condition:
    metric: str
    op: Op
    threshold_value: float

    def evaluate(self, context: dict[str, float]) -> bool:
        v = context.get(self.metric)
        if v is None:
            return False
        return bool(_OPS[self.op](float(v), self.threshold_value))


@dataclass(frozen=True, slots=True)
class _Rule:
    id: str
    description: str
    policy: ContradictionPolicy
    severity: float
    conditions: tuple[_Condition, ...]


@dataclass(frozen=True, slots=True)
class ContradictionContext:
    """Numeric context consumed by the matrix evaluator.

    Every metric referenced in `rules.yaml` MUST be supplied here (missing
    metrics cause the rule's condition to evaluate False, which is safe by
    construction but suppressible — the orchestrator is expected to populate
    every metric explicitly).
    """

    pathology_aggregate: float
    structural_health: float
    instability_score: float
    escalation_risk: float

    entropy_instability: float
    autocorrelation_breakdown: float
    liquidity_imbalance: float
    dispersion_shock: float
    volatility_disorder: float
    continuation_decay: float

    continuation_confidence: float
    trend_persistence_health: float
    structural_fragmentation: float
    expansion_sustainability: float
    structural_balance: float
    continuation_state_strength: float

    defensive_posture: float = 0.0
    aggressive_participation: float = 0.0
    regime_is_defensive: float = 0.0

    macro_instability: float = 0.0
    local_expansion_health: float = 0.0
    timeframe_collapse_risk: float = 0.0
    local_optimism: float = 0.0

    contradiction_score_prior: float = 0.0
    pre_aggregation_confidence: float = 0.0

    extra: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, float]:
        out = {
            "pathology_aggregate": self.pathology_aggregate,
            "structural_health": self.structural_health,
            "instability_score": self.instability_score,
            "escalation_risk": self.escalation_risk,
            "entropy_instability": self.entropy_instability,
            "autocorrelation_breakdown": self.autocorrelation_breakdown,
            "liquidity_imbalance": self.liquidity_imbalance,
            "dispersion_shock": self.dispersion_shock,
            "volatility_disorder": self.volatility_disorder,
            "continuation_decay": self.continuation_decay,
            "continuation_confidence": self.continuation_confidence,
            "trend_persistence_health": self.trend_persistence_health,
            "structural_fragmentation": self.structural_fragmentation,
            "expansion_sustainability": self.expansion_sustainability,
            "structural_balance": self.structural_balance,
            "continuation_state_strength": self.continuation_state_strength,
            "defensive_posture": self.defensive_posture,
            "aggressive_participation": self.aggressive_participation,
            "regime_is_defensive": self.regime_is_defensive,
            "macro_instability": self.macro_instability,
            "local_expansion_health": self.local_expansion_health,
            "timeframe_collapse_risk": self.timeframe_collapse_risk,
            "local_optimism": self.local_optimism,
            "contradiction_score_prior": self.contradiction_score_prior,
            "pre_aggregation_confidence": self.pre_aggregation_confidence,
        }
        out.update(self.extra)
        return out


@lru_cache(maxsize=8)
def load_default_rules(path: str = str(DEFAULT_RULES_PATH)) -> tuple[tuple[_Rule, ...], dict[str, float]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("contradiction rules.yaml must be a mapping")
    thresholds_raw = raw.get("thresholds")
    if not isinstance(thresholds_raw, dict) or "HIGH" not in thresholds_raw or "LOW" not in thresholds_raw:
        raise ValueError("rules.yaml must define thresholds.HIGH and thresholds.LOW")
    thresholds: dict[str, float] = {k: float(v) for k, v in thresholds_raw.items()}
    rules_raw = raw.get("rules", [])
    if not isinstance(rules_raw, list):
        raise ValueError("rules.yaml.rules must be a list")
    rules: list[_Rule] = []
    for r in rules_raw:
        policy_str = r["policy"]
        try:
            policy = ContradictionPolicy(policy_str)
        except ValueError as exc:
            raise ValueError(f"unknown policy {policy_str!r} in rule {r.get('id')!r}") from exc
        conds: list[_Condition] = []
        for c in r.get("conditions", []):
            thr_name = c["threshold"]
            thr_value = thresholds[thr_name] if isinstance(thr_name, str) else float(thr_name)
            conds.append(
                _Condition(
                    metric=c["metric"],
                    op=c["op"],
                    threshold_value=float(thr_value),
                )
            )
        rules.append(
            _Rule(
                id=r["id"],
                description=r["description"],
                policy=policy,
                severity=float(r.get("severity", 0.5)),
                conditions=tuple(conds),
            )
        )
    return tuple(rules), thresholds


class ContradictionMatrix:
    """Stateless evaluator of the loaded contradiction rule set."""

    def __init__(self, rules_path: Path | None = None) -> None:
        path = rules_path or DEFAULT_RULES_PATH
        self.rules, self.thresholds = load_default_rules(str(path))

    @property
    def high_threshold(self) -> float:
        return self.thresholds["HIGH"]

    @property
    def low_threshold(self) -> float:
        return self.thresholds["LOW"]

    def evaluate(self, context: ContradictionContext) -> list[tuple[_Rule, float]]:
        ctx = context.to_dict()
        findings: list[tuple[_Rule, float]] = []
        for rule in self.rules:
            if not rule.conditions:
                continue
            if all(cond.evaluate(ctx) for cond in rule.conditions):
                findings.append((rule, rule.severity))
        return findings
