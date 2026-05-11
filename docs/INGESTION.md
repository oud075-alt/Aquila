# Real-time Market Ingestion (SPECIFIED — interface + in-proc adapter)

## Schema (immutable, idempotent, lineage-tagged)

```python
class RawEvent(BaseModel, frozen=True):
    event_id: str
    schema_version: str
    kind: RawEventKind          # tick | ohlcv | orderflow | macro | synthetic
    symbol: Symbol
    timestamp: datetime          # exchange-reported
    received_at: datetime        # ingestion-receive time
    source_id: str
    trust_score: float           # 0..1
    origin: Origin               # real | synthetic | replay
    idempotency_key: str | None
    ohlcv: OHLCV | None
    orderflow: OrderFlowEvent | None
    macro: MacroEvent | None
    raw_payload: dict
```

## Pipeline

```
Adapter.stream() → IngestionNormalizer.ingest(event)
                       │  ├─ dedup via idempotency_key
                       │  ├─ ensure UTC tz on timestamp
                       │  └─ propagate source_id / trust_score
                       ▼
                   Orchestrator.run_tick(symbol, bar)
```

## Supported event streams (interface-level, in-proc adapter shipped)

- `OHLCV` ticks ✅
- `OrderFlowEvent` (price/size/side/aggressive flag) — interface ready
- `MacroEvent` (indicator/value/surprise) — interface ready
- Cross-asset feeds — handled by spinning up an orchestrator per symbol
- Synthetic feeds — `RawEvent.origin="synthetic"` (refused by real memory)
- Tick streams — represented as OHLCV at M1 (or below) for the cognitive
  pipeline; sub-second microstructure would extend Layer 0 only.

## Production gateways (TBD)

- Exchange WebSockets via `MarketDataAdapter` subclasses
- Kafka consumer adapter
- File-based replay (already shipped via `ReplayAdapter`)

## Determinism guarantees

- Each `RawEvent` carries `timestamp` (exchange time) — sole basis for
  ordering during replay.
- `idempotency_key` lets replays from multiple feeds dedupe deterministically.
- `origin` prevents synthetic / replay events from contaminating the
  real episodic archive (enforced by `EpisodicMemoryLayer`).

## Integrity validation

`IngestionAuditLayer` (out of scope here, interface-level) would record
every received `RawEvent` to an append-only log distinct from the
cognitive audit log. Production deployments may sign log heads.
