"""CQRS read-model projections over the EventStore."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from aquila.core.types import LayerName, Symbol
from aquila.governance.eventstore import StoredEvent


class Projection:
    def __init__(self) -> None:
        self._by_symbol: dict[Symbol, list[StoredEvent]] = defaultdict(list)

    def ingest(self, events: Iterable[StoredEvent]) -> None:
        for e in events:
            self._by_symbol[e.symbol].append(e)

    def structural_states(self, symbol: Symbol, last_n: int) -> list[str]:
        evs = [e for e in self._by_symbol.get(symbol, []) if e.layer == LayerName.STRUCTURAL]
        return [e.payload.get("state", "unknown") for e in evs[-last_n:]]

    def pathology_history(self, symbol: Symbol, last_n: int) -> tuple[list[float], list[float]]:
        evs = [e for e in self._by_symbol.get(symbol, []) if e.layer == LayerName.PATHOLOGY]
        ps = [float(e.payload.get("aggregate_pathology_score", 0.0)) for e in evs[-last_n:]]
        cs = [float(e.payload.get("aggregate_contradiction_score", 0.0)) for e in evs[-last_n:]]
        return ps, cs

    def by_correlation(self, correlation_id: str) -> list[StoredEvent]:
        out: list[StoredEvent] = []
        for evs in self._by_symbol.values():
            out.extend(e for e in evs if e.correlation_id == correlation_id)
        return out
