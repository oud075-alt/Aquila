# Runtime Architecture (SPECIFIED — not fully implemented)

## In-process default (this PR)

```
                ┌─────────────────────────────┐
                │  CognitiveOrchestrator      │
                │   (single process)          │
                │                             │
                │   L1 → L2 → L3 → {L4..L7}   │
                │           │                 │
                │           ▼                 │
                │          L8                 │
                └──────────────┬──────────────┘
                               │
            ┌──────────────────┼─────────────────────┐
            ▼                  ▼                     ▼
       EventBus (in-proc)  AuditLog (hash-chain)  EventStore (append-only)
```

## Distributed runtime (interfaces shipped, transport TBD)

Replace `EventBus` with an `EventTransport` implementation. Two
plausible options:

1. **NATS JetStream** — at-least-once delivery, deterministic ordering
   per partition; matches our per-symbol orchestrator semantics.
2. **Kafka** — exactly-once via idempotent producer + transactional
   consumer; higher operational cost but full replay.

The `EventTransport` interface in `aquila/runtime/transport.py` is:

```python
class EventTransport(ABC):
    def publish(self, output: LayerOutput) -> None: ...
    def subscribe(self, layer: LayerName, handler: Handler) -> None: ...
```

This intentionally matches `EventBus`'s shape so a swap is mechanical.

## Worker model

- **One orchestrator per (symbol, replay_run)**.
- Layers are stateless except for `Layer 4` (memory) which is durable per
  symbol — symbol shard key is the partitioning unit.
- L7 calibration is per-symbol; `AdaptiveCalibrator` instances are
  scoped to each orchestrator.

## Replay isolation

`ReplayRunner` constructs its own `CognitiveOrchestrator` with:
- `ReplayClock` (frozen, advances via event timestamps)
- `EpisodicMemoryLayer(write_on_real=False)` (no archive contamination)
- `origin="replay"` propagated through every `LayerContext`

## Liveness / readiness

`aquila/api/routes/health.py`:
- `GET /health/live` → always 200 if process alive
- `GET /health/ready` → 200 + `audit_chain_ok` + `events_stored`

## Backpressure & load-shedding (SPECIFIED)

`aquila/failure/load_shed.py` defines a policy hook. When `Telemetry`
reports cycle latency exceeding `cycle_latency_budget_ms`, optional
subsystems (narrative, intermarket, attention) are skipped. Core
cognition (L1–L8) is never shed.
