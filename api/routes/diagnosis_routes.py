"""Diagnosis endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from brain.execution.report_generator import ReportGenerator
from brain.orchestrator import Orchestrator
from brain.schemas import StandardizedDiagnosis


router = APIRouter(tags=["diagnosis"])
_report = ReportGenerator()


def _get_orchestrator(request: Request) -> Orchestrator:
    orchestrator: Orchestrator = request.app.state.orchestrator
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised")
    return orchestrator


@router.get("/diagnosis")
async def diagnosis(
    request: Request,
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="1m"),
    exchange: str = Query(default="binance"),
    include_gpt: bool = Query(default=True),
) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    diag = await orchestrator.diagnose_symbol(
        symbol=symbol, timeframe=timeframe, exchange=exchange, include_gpt=include_gpt
    )
    return diag.to_dict()


@router.get("/market/state")
async def market_state(
    request: Request,
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="1m"),
    exchange: str = Query(default="binance"),
) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    diag = await orchestrator.diagnose_symbol(symbol=symbol, timeframe=timeframe, exchange=exchange, include_gpt=False)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "exchange": exchange,
        "market_state": diag.market_state.value,
        "severity": diag.severity.value,
        "regime": diag.regime.value,
        "overall_pathology": diag.overall_pathology(),
        "confidence": diag.confidence_scores.overall_confidence,
        "structural_health": diag.structural_health.model_dump(),
        "transition_state": diag.transition_state.model_dump(),
    }


@router.get("/pathology")
async def pathology(
    request: Request,
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="1m"),
    exchange: str = Query(default="binance"),
) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    diag = await orchestrator.diagnose_symbol(symbol=symbol, timeframe=timeframe, exchange=exchange, include_gpt=False)
    return {
        "scores": diag.pathology_scores.as_dict(),
        "aggregate": diag.overall_pathology(),
        "ranked": diag.extra.get("ranked_pathologies", []),
    }


@router.get("/anomaly")
async def anomaly(
    request: Request,
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="1m"),
    exchange: str = Query(default="binance"),
) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    diag = await orchestrator.diagnose_symbol(symbol=symbol, timeframe=timeframe, exchange=exchange, include_gpt=False)
    return {
        "contradictions": diag.contradiction_scores.as_dict(),
        "causal_reasoning": diag.causal_reasoning,
        "expectation": diag.expectation.model_dump(),
        "actual": diag.actual.model_dump(),
    }


@router.get("/stress")
async def stress(
    request: Request,
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="1m"),
    exchange: str = Query(default="binance"),
) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    diag = await orchestrator.diagnose_symbol(symbol=symbol, timeframe=timeframe, exchange=exchange, include_gpt=False)
    return {
        "stress_escalation": diag.pathology_scores.stress_escalation,
        "liquidity_fragility": diag.pathology_scores.liquidity_fragility,
        "escalation_risk": diag.escalation_risk.model_dump(),
        "volatility_state": diag.volatility_state.model_dump(),
        "instability_state": diag.instability_state.model_dump(),
    }


@router.get("/report")
async def report(
    request: Request,
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="1m"),
    exchange: str = Query(default="binance"),
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
) -> Any:
    orchestrator = _get_orchestrator(request)
    diag = await orchestrator.diagnose_symbol(symbol=symbol, timeframe=timeframe, exchange=exchange, include_gpt=True)
    if format == "json":
        return diag.to_dict()
    md = _report.build_markdown(diag)
    return {"format": "markdown", "content": md}


@router.get("/alerts")
async def alerts(request: Request, limit: int = Query(default=50, le=500)) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    return {"alerts": orchestrator.alert_engine.recent(limit=limit)}


@router.get("/memory/recent")
async def memory_recent(request: Request, limit: int = Query(default=20, le=500)) -> Dict[str, Any]:
    orchestrator = _get_orchestrator(request)
    return {"history": orchestrator.memory_core.recent_history(limit=limit)}
