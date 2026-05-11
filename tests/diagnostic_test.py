"""Diagnostic correctness tests — direct module unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from brain.expectation.expected_behavior_engine import ExpectedBehaviorEngine
from brain.intelligence.actual_behavior_engine import ActualBehaviorEngine
from brain.intelligence.contradiction_engine import ContradictionEngine
from brain.intelligence.disease_classifier import DiseaseClassifier
from brain.intelligence.market_diagnosis_engine import MarketDiagnosisEngine
from brain.pathology.anomaly_detector import AnomalyDetector
from brain.schemas import Candle, RegimeLabel, SeverityLevel


def _make_candles(n: int = 400, regime: str = "trend_up") -> list:
    rng = np.random.default_rng(seed=12345)
    base = 100.0
    candles = []
    now = datetime.now(timezone.utc)
    drift_map = {
        "trend_up": 0.0010,
        "trend_down": -0.0010,
        "chop": 0.0,
        "compression": 0.0,
        "expansion": 0.0,
    }
    drift = drift_map.get(regime, 0.0)
    vol = 0.004 if regime != "compression" else 0.001
    price = base
    for i in range(n):
        r = drift + vol * rng.standard_normal()
        price *= (1 + r)
        o = price * (1 - r * 0.5)
        c = price
        h = max(o, c) * (1 + abs(r) * 0.4 + 0.0005)
        l = min(o, c) * (1 - abs(r) * 0.4 - 0.0005)
        v = max(1.0, 1000 + rng.standard_normal() * 200)
        ts = now - timedelta(minutes=(n - i))
        candles.append(Candle(timestamp=ts, open=o, high=h, low=l, close=c, volume=v))
    return candles


def test_expectation_engine_produces_profile():
    candles = _make_candles(400, "trend_up")
    eng = ExpectedBehaviorEngine()
    profile = eng.build(candles)
    assert profile.regime in list(RegimeLabel)
    assert profile.expected_volatility >= 0.0
    assert 0.0 <= profile.expected_acceptance <= 1.0


def test_actual_behavior_engine_produces_profile():
    candles = _make_candles(400, "trend_up")
    eng = ActualBehaviorEngine()
    actual = eng.measure(candles)
    assert -1.0 <= actual.realized_breakout_followthrough <= 2.0
    assert 0.0 <= actual.realized_acceptance <= 1.0


def test_anomaly_detector_returns_bounded_probs():
    candles = _make_candles(400, "trend_up")
    expected = ExpectedBehaviorEngine().build(candles)
    actual = ActualBehaviorEngine().measure(candles)
    res = AnomalyDetector().evaluate(expected, actual)
    for p in res.probabilities.values():
        assert 0.0 <= p <= 1.0
    assert 0.0 <= res.aggregate <= 1.0


def test_contradiction_engine_produces_scores_and_reasoning():
    candles = _make_candles(400, "trend_up")
    expected = ExpectedBehaviorEngine().build(candles)
    actual = ActualBehaviorEngine().measure(candles)
    c = ContradictionEngine().evaluate(expected, actual)
    for v in c.scores.as_dict().values():
        assert 0.0 <= v <= 1.0
    assert len(c.reasoning) >= 1


def test_market_diagnosis_engine_outputs_pathology_bundle():
    candles = _make_candles(400, "trend_up")
    expected = ExpectedBehaviorEngine().build(candles)
    actual = ActualBehaviorEngine().measure(candles)
    bundle = MarketDiagnosisEngine().diagnose(candles, expected, actual, ticks=[])
    for v in bundle.pathology.as_dict().values():
        assert 0.0 <= v <= 1.0
    assert 0.0 <= bundle.pathology.aggregate() <= 1.0


def test_disease_classifier_assigns_severity_within_hierarchy():
    candles = _make_candles(400, "trend_up")
    expected = ExpectedBehaviorEngine().build(candles)
    actual = ActualBehaviorEngine().measure(candles)
    bundle = MarketDiagnosisEngine().diagnose(candles, expected, actual, ticks=[])
    contradiction = ContradictionEngine().evaluate(expected, actual).scores
    classification = DiseaseClassifier().classify(
        pathology=bundle.pathology,
        contradiction=contradiction,
        regime=expected.regime,
        compression_release_prob=bundle.compression_release_prob,
    )
    assert isinstance(classification.severity, SeverityLevel)
    assert 0.0 <= classification.score <= 1.0


def test_pre_collapse_combines_correctly():
    from brain.pathology import PreCollapseModel
    pc = PreCollapseModel()
    assess = pc.evaluate(0.8, 0.7, 0.7, 0.6, 0.6, 0.7, bull_bias=1.0)
    assert assess.score >= 0.5
    assert assess.direction in ("DOWNSIDE", "UPSIDE_RELEASE", "NEUTRAL")
