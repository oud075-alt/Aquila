"""Ingestion interfaces — adapter + gateway contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from aquila.ingestion.schemas import RawEvent


class MarketDataAdapter(ABC):
    """Pluggable adapter: exchange WebSocket, file replay, Kafka consumer."""

    source_id: str

    @abstractmethod
    def stream(self) -> Iterator[RawEvent]:  # pragma: no cover - interface
        raise NotImplementedError


class IngestionGateway(ABC):
    @abstractmethod
    def ingest(self, event: RawEvent) -> RawEvent | None:  # pragma: no cover
        """Normalize, dedupe, validate. Return None if dropped."""
        raise NotImplementedError
