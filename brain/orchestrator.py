"""Brain orchestrator — single entry point for the intelligence pipeline.

Implements the MANDATORY INTELLIGENCE FLOW:

1. MARKET SENSORY INGESTION
2. EXPECTED HEALTHY STRUCTURE MODELING
3. ACTUAL MARKET BEHAVIOR ANALYSIS
4. CONTRADICTION DETECTION
5. PATHOLOGY SCORING
6. DISEASE CLASSIFICATION
7. STATE TRANSITION ANALYSIS
8. RISK ESCALATION FORECAST
9. DIAGNOSTIC REPORT GENERATION
10. MEMORY STORAGE + LEARNING

Every module participates in this chain. Failures in optional components
(e.g. GPT, news, calendar) degrade gracefully without breaking the
pipeline.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from brain.execution.alert_engine import AlertEngine
from brain.execution.report_generator import ReportGenerator
from brain.execution.risk_escalation_alert import RiskEscalationAlert
from brain.execution.scenario_projection import ScenarioProjection
from brain.expectation.expected_behavior_engine import ExpectedBehaviorEngine
from brain.gpt.market_explainer import MarketExplainer
from brain.intelligence.actual_behavior_engine import ActualBehaviorEngine
from brain.intelligence.confidence_engine import ConfidenceEngine
from brain.intelligence.contradiction_engine import ContradictionEngine
from brain.intelligence.disease_classifier import DiseaseClassifier
from brain.intelligence.market_diagnosis_engine import MarketDiagnosisEngine
from brain.intelligence.pathology_ranker import PathologyRanker
from brain.intelligence.state_transition_engine import StateTransitionEngine
from brain.logging_utils import get_logger
from brain.math_core import clamp
from brain.memory_core import MemoryCore
from brain.schemas import (
    Candle,
    MarketSnapshot,
    StandardizedDiagnosis,
    StructuralHealth,
)
from brain.sensory.binance_feed import BinanceFeed
from brain.sensory.base import DataFeed
from brain.sensory.mt5_feed import MT5Feed
from brain.sensory.tradingview_feed import TradingViewFeed
from brain.sensory.economic_calendar import EconomicCalendar
from brain.sensory.news_stream import NewsStream
from config import get_market_config, get_settings


class Orchestrator:
    """The MSPIS brain — coordinates every cognitive layer."""

    def __init__(self):
        self.log = get_logger("mspis.orchestrator")
        self.settings = get_settings()
        self.market_cfg = get_market_config()

        # Intelligence components
        self.expected_engine = ExpectedBehaviorEngine()
        self.actual_engine = ActualBehaviorEngine()
        self.contradiction_engine = ContradictionEngine()
        self.disease_classifier = DiseaseClassifier()
        self.market_diagnosis = MarketDiagnosisEngine()
        self.confidence_engine = ConfidenceEngine()
        self.state_transition_engine = StateTransitionEngine()
        self.pathology_ranker = PathologyRanker()
        self.risk_escalation = RiskEscalationAlert()
        self.scenario_projection = ScenarioProjection()
        self.alert_engine = AlertEngine()
        self.report_generator = ReportGenerator()
        self.market_explainer = MarketExplainer()
        self.memory_core = MemoryCore()

        # Sensory side caches
        self._feeds: Dict[tuple, DataFeed] = {}
        self.news_stream = NewsStream()
        self.economic_calendar = EconomicCalendar()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def diagnose_symbol(
        self,
        symbol: str,
        timeframe: str = "1m",
        exchange: str = "binance",
        include_gpt: bool = True,
    ) -> StandardizedDiagnosis:
        """Run one full diagnostic cycle for ``symbol`` at ``timeframe``."""
        snapshot = await self.ingest_snapshot(symbol=symbol, timeframe=timeframe, exchange=exchange)
        return await self.diagnose_snapshot(snapshot, include_gpt=include_gpt)

    async def diagnose_snapshot(
        self,
        snapshot: MarketSnapshot,
        include_gpt: bool = True,
    ) -> StandardizedDiagnosis:
        """Run the diagnostic pipeline on an already ingested snapshot."""
        # ---- 1. Validity gate -------------------------------------------------
        if not snapshot.is_valid(min_bars=self.market_cfg.min_bars_for_diagnosis):
            self.log.warning(
                "Snapshot %s/%s has only %d bars (<%d) — diagnosis will be low-confidence",
                snapshot.symbol, snapshot.timeframe,
                len(snapshot.candles), self.market_cfg.min_bars_for_diagnosis,
            )

        # ---- 2. Expected behaviour -------------------------------------------
        expected = self.expected_engine.build(snapshot.candles)

        # ---- 3. Actual behaviour ---------------------------------------------
        actual = self.actual_engine.measure(snapshot.candles)

        # ---- 4. Contradictions -----------------------------------------------
        contradiction = self.contradiction_engine.evaluate(expected, actual)

        # ---- 5. Pathology scoring --------------------------------------------
        bundle = self.market_diagnosis.diagnose(
            candles=snapshot.candles,
            expected=expected,
            actual=actual,
            ticks=snapshot.ticks,
        )

        # ---- 6. Disease classification ---------------------------------------
        classification = self.disease_classifier.classify(
            pathology=bundle.pathology,
            contradiction=contradiction.scores,
            regime=expected.regime,
            compression_release_prob=bundle.compression_release_prob,
        )

        # ---- 7. Confidence ---------------------------------------------------
        confidence = self.confidence_engine.evaluate(
            candles=snapshot.candles,
            expected=expected,
            actual=actual,
            pathology=bundle.pathology,
            contradiction=contradiction.scores,
        )

        # ---- 8. Transition ---------------------------------------------------
        transition = self.state_transition_engine.update(
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            new_label=classification.label,
            new_severity=classification.severity,
        )

        # ---- 9. Escalation + projection --------------------------------------
        bull_bias = float(1.0 if actual.realized_trend_slope > 0 else -1.0 if actual.realized_trend_slope < 0 else 0.0)
        escalation = self.risk_escalation.compute(
            pathology=bundle.pathology,
            transition=transition,
            compression_release_prob=bundle.compression_release_prob,
            bull_bias=bull_bias,
        )

        # ---- 10. Structural health ------------------------------------------
        health = self._structural_health(bundle, contradiction.scores, escalation, transition)

        # ---- Assemble diagnosis ---------------------------------------------
        causal_reasoning: List[str] = []
        causal_reasoning.extend(contradiction.reasoning)
        causal_reasoning.extend(classification.reasoning)
        ranked = self.pathology_ranker.rank(bundle.pathology, contradiction.scores)
        top_ranked = [
            f"top pathology contributor: {r.name} (score={r.score:.2f}, weighted={r.weighted_score:.2f})"
            for r in ranked[:3]
        ]
        causal_reasoning.extend(top_ranked)

        diag = StandardizedDiagnosis(
            timestamp=datetime.now(timezone.utc),
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            exchange=snapshot.exchange,
            market_state=classification.label,
            severity=classification.severity,
            regime=expected.regime,
            expectation=expected,
            actual=actual,
            pathology_scores=bundle.pathology,
            contradiction_scores=contradiction.scores,
            volatility_state=bundle.volatility_state,
            liquidity_state=bundle.liquidity_state,
            continuation_state=bundle.continuation_state,
            instability_state=bundle.instability_state,
            confidence_scores=confidence,
            escalation_risk=escalation,
            structural_health=health,
            transition_state=transition,
            causal_reasoning=causal_reasoning,
            extra={
                "orderflow": bundle.orderflow.to_dict(),
                "pre_collapse_direction": bundle.pre_collapse_direction,
                "compression_release_probability": bundle.compression_release_prob,
                "component_features": bundle.component_features,
                "ranked_pathologies": [
                    {"name": r.name, "score": r.score, "weighted": r.weighted_score}
                    for r in ranked
                ],
                "news_events": snapshot.news_events[:5],
                "economic_events": snapshot.economic_events[:5],
            },
        )

        # ---- GPT explanation -------------------------------------------------
        if include_gpt:
            try:
                diag.gpt_interpretation = await self.market_explainer.explain(diag)
            except Exception as e:
                self.log.debug("GPT explain failed: %s", e)
                diag.gpt_interpretation = None

        # ---- Scenario projection summary ------------------------------------
        projection = self.scenario_projection.project(diag)
        diag.extra["projection"] = {
            "next_regime_probabilities": projection.next_regime_probabilities,
            "collapse_probability": projection.collapse_probability,
            "expansion_probability": projection.expansion_probability,
            "continuation_probability": projection.continuation_probability,
            "transition_probability": projection.transition_probability,
            "horizon_bars": projection.horizon_bars,
            "rationale": projection.rationale,
        }

        # ---- Diagnostic summary --------------------------------------------
        diag.diagnostic_summary = self._summary_text(diag)

        # ---- Memory + alerts ------------------------------------------------
        try:
            self.memory_core.absorb(diag)
        except Exception as e:
            self.log.warning("memory absorb failed: %s", e)

        try:
            alerts = await self.alert_engine.evaluate(diag)
            diag.extra["alerts"] = alerts
        except Exception as e:
            self.log.warning("alert engine failed: %s", e)
            diag.extra.setdefault("alerts", [])

        return diag

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    async def ingest_snapshot(
        self,
        symbol: str,
        timeframe: str = "1m",
        exchange: str = "binance",
    ) -> MarketSnapshot:
        feed = await self._get_feed(symbol=symbol, timeframe=timeframe, exchange=exchange)
        candles = await feed.fetch_candles(lookback=self.settings.history_bars)

        # Fault tolerance: if the live feed returns very few bars, top up with
        # the synthetic generator so the downstream pipeline still has enough
        # signal to operate. This is required behaviour per spec.
        if len(candles) < self.market_cfg.min_bars_for_diagnosis:
            synthetic = feed._synthetic_candles(  # type: ignore[attr-defined]
                self.market_cfg.min_bars_for_diagnosis + 50,
                seed=hash((symbol, timeframe)) & 0xFFFF,
            )
            existing_ts = {c.timestamp for c in candles}
            for c in synthetic:
                if c.timestamp not in existing_ts:
                    candles.append(c)
            candles.sort(key=lambda c: c.timestamp)

        # Try to enrich with news + calendar (best-effort)
        news_events: List[Dict[str, Any]] = []
        econ_events: List[Dict[str, Any]] = []
        try:
            news_events = await asyncio.wait_for(self.news_stream.poll([symbol]), timeout=8.0)
        except Exception:
            pass
        try:
            econ_events = await asyncio.wait_for(self.economic_calendar.upcoming(), timeout=8.0)
        except Exception:
            pass

        return MarketSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            exchange=exchange,
            candles=candles[-self.settings.history_bars :],
            last_price=candles[-1].close if candles else None,
            news_events=news_events,
            economic_events=econ_events,
        )

    async def _get_feed(self, symbol: str, timeframe: str, exchange: str) -> DataFeed:
        key = (exchange, symbol, timeframe)
        if key in self._feeds:
            return self._feeds[key]
        exchange_l = exchange.lower()
        if exchange_l in ("mt5", "metatrader", "metatrader5"):
            feed: DataFeed = MT5Feed(symbol=symbol, timeframe=timeframe)
        elif exchange_l in ("tradingview", "tv"):
            feed = TradingViewFeed(symbol=symbol, timeframe=timeframe)
        else:
            feed = BinanceFeed(symbol=symbol, timeframe=timeframe)
        await feed.connect()
        self._feeds[key] = feed
        return feed

    async def shutdown(self) -> None:
        for feed in self._feeds.values():
            try:
                await feed.close()
            except Exception:
                pass
        try:
            await self.news_stream.close()
        except Exception:
            pass
        try:
            await self.economic_calendar.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Derived computations
    # ------------------------------------------------------------------
    def _structural_health(self, bundle, contradiction_scores, escalation, transition) -> StructuralHealth:
        agg = bundle.pathology.aggregate()
        contradiction_load = (
            sum(contradiction_scores.as_dict().values()) / max(1, len(contradiction_scores.as_dict()))
        )
        physiology_alignment = clamp(
            1.0
            - 0.5 * bundle.pathology.behavioral_divergence
            - 0.3 * bundle.pathology.acceptance_failure
            - 0.2 * bundle.pathology.continuation_failure,
            0.0,
            1.0,
        )
        score = clamp(1.0 - (0.55 * agg + 0.25 * contradiction_load + 0.2 * escalation.pressure_build_rate), 0.0, 1.0)
        deterioration = clamp(
            0.5 * float(max(0.0, transition.transition_velocity))
            + 0.5 * escalation.pressure_build_rate,
            0.0,
            1.0,
        )
        if score >= 0.75:
            summary = "healthy"
        elif score >= 0.55:
            summary = "minor stress"
        elif score >= 0.35:
            summary = "fragile"
        elif score >= 0.20:
            summary = "high risk"
        else:
            summary = "critical"
        return StructuralHealth(
            score=score,
            physiology_alignment=physiology_alignment,
            deterioration_velocity=deterioration,
            summary=summary,
        )

    @staticmethod
    def _summary_text(diag: StandardizedDiagnosis) -> str:
        top = sorted(diag.pathology_scores.as_dict().items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_str = ", ".join(f"{k}={v:.2f}" for k, v in top)
        return (
            f"{diag.symbol} {diag.timeframe} ({diag.exchange}): "
            f"{diag.market_state.value} | {diag.severity.value} | "
            f"regime={diag.regime.value} | aggregate_pathology="
            f"{diag.overall_pathology():.2f} | confidence="
            f"{diag.confidence_scores.overall_confidence:.2f} | "
            f"top_contributors=[{top_str}] | "
            f"structural_health={diag.structural_health.score:.2f} "
            f"({diag.structural_health.summary})."
        )
