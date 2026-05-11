"""Distributed runtime — interfaces only.

This subsystem is **SPECIFIED**: typed interfaces and an in-proc default
implementation. Production deployments swap `InProcTransport` with a
Kafka/NATS/gRPC implementation that fulfills the same contract.

See `docs/RUNTIME.md` for the distributed architecture.
"""

from aquila.runtime.scheduler import ReplayScheduler
from aquila.runtime.supervisor import CognitionSupervisor
from aquila.runtime.transport import EventTransport, InProcTransport

__all__ = ["EventTransport", "InProcTransport", "ReplayScheduler", "CognitionSupervisor"]
