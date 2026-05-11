"""FastAPI application factory + entry point.

Run with:

.. code-block:: bash

    uvicorn api.server:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from brain.logging_utils import get_logger
from brain.orchestrator import Orchestrator
from config import get_settings


_log = get_logger("mspis.api.server")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _log.info("Starting MSPIS API (env=%s)", settings.env)
    orchestrator = Orchestrator()
    app.state.orchestrator = orchestrator
    try:
        yield
    finally:
        _log.info("Shutting down MSPIS API")
        try:
            await orchestrator.shutdown()
        except Exception:
            pass


def get_orchestrator(app: FastAPI = None) -> Orchestrator:  # pragma: no cover (DI used through Depends)
    from fastapi import Request

    def _provider(request: Request) -> Orchestrator:
        return request.app.state.orchestrator

    return _provider  # type: ignore[return-value]


async def _auth(authorization: str | None = Header(default=None)) -> None:
    """Optional bearer auth. If `MSPIS_API_KEY` is unset, auth is disabled."""
    expected = get_settings().api_key
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Market Structural Pathology Intelligence System (MSPIS)",
        version="1.0.0",
        description=(
            "Diagnostic intelligence for financial markets. Detects internal "
            "structural disease before external price collapse or expansion "
            "becomes visible. NOT a trading bot — NOT a signal generator."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["meta"], dependencies=[Depends(_auth)])
    async def root():
        return {
            "system": "MSPIS",
            "version": "1.0.0",
            "env": settings.env,
            "purpose": "Structural pathology diagnosis. NOT a signal engine.",
            "endpoints": [
                "/diagnosis", "/health", "/market/state", "/pathology",
                "/anomaly", "/stress", "/report",
            ],
        }

    from .routes import diagnosis_routes, health_routes
    app.include_router(diagnosis_routes.router, dependencies=[Depends(_auth)])
    app.include_router(health_routes.router, dependencies=[Depends(_auth)])

    return app


app = create_app()


def main() -> None:  # pragma: no cover
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
