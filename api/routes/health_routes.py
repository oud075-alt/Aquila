"""Health / readiness endpoints."""

from __future__ import annotations

import platform
import time
from typing import Any, Dict

from fastapi import APIRouter, Request

from brain.orchestrator import Orchestrator
from config import get_api_keys, get_settings


router = APIRouter(tags=["health"])
_BOOT_TS = time.time()


@router.get("/health")
async def health(request: Request) -> Dict[str, Any]:
    settings = get_settings()
    keys = get_api_keys()
    orchestrator: Orchestrator | None = getattr(request.app.state, "orchestrator", None)
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - _BOOT_TS),
        "python_version": platform.python_version(),
        "env": settings.env,
        "orchestrator_loaded": orchestrator is not None,
        "openai_available": keys.has_openai(),
        "binance_credentials": keys.has_binance(),
        "mt5_credentials": keys.has_mt5(),
        "data_dir": str(settings.data_dir),
        "memory_dir": str(settings.memory_dir),
    }


@router.get("/health/components")
async def health_components(request: Request) -> Dict[str, Any]:
    orchestrator: Orchestrator | None = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        return {"status": "no orchestrator"}
    return {
        "feeds": list(orchestrator._feeds.keys()),  # type: ignore[arg-type]
        "memory_stats": orchestrator.memory_core.adaptive.stats(),
        "alerts_recent": len(orchestrator.alert_engine.recent(limit=100)),
    }
