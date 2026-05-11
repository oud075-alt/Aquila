from __future__ import annotations

from aquila.observability.telemetry import Telemetry


class CognitionSupervisor:
    """Supervises a worker / orchestrator. Reports liveness + telemetry.

    In-proc default: liveness is always true if the supervisor was
    constructed. Distributed: heartbeat-driven.
    """

    def __init__(self, telemetry: Telemetry) -> None:
        self._telemetry = telemetry
        self._alive = True

    def liveness(self) -> bool:
        return self._alive

    def readiness(self) -> bool:
        return self._alive

    def snapshot(self) -> dict:
        return self._telemetry.snapshot()
