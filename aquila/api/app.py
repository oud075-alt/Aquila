from __future__ import annotations

from fastapi import FastAPI

from aquila.api.routes import (
    cognition,
    feedback,
    health,
    intermarket,
    memory,
    narrative,
    query,
    replay,
    simulation,
    validation,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Aquila / MSPIS Cognitive Architecture",
        version="0.1.0",
        description=(
            "Institutional market cognition engine. NOT a trading bot, NOT a "
            "signal generator. Diagnoses structural pathology, deception, "
            "regime mutation, and cognitive uncertainty."
        ),
    )
    app.include_router(health.router)
    app.include_router(cognition.router)
    app.include_router(memory.router)
    app.include_router(query.router)
    app.include_router(replay.router)
    app.include_router(simulation.router)
    app.include_router(validation.router)
    app.include_router(narrative.router)
    app.include_router(intermarket.router)
    app.include_router(feedback.router)
    return app


app = create_app()
