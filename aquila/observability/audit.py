"""Hash-chained audit log. Closes audit gap #62.

Each record carries the SHA-256 hash of the previous record AND a SHA-256
hash of the layer output payload. Tampering with the chain header, the
confidence/visibility metadata, or the payload body all invalidate the
chain from that point forward.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName


def _hash_payload(output: LayerOutput) -> str:
    """SHA-256 of the layer output payload, computed deterministically.

    Sorted keys plus ``default=str`` make this stable across datetimes and
    other non-JSON-native fields contained in payloads.
    """
    blob = json.dumps(
        output.payload.model_dump(),
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class AuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    layer: LayerName
    correlation_id: str
    event_id: str
    confidence: float
    visibility: str
    payload_hash: str = ""
    prev_hash: str = ""
    record_hash: str = ""

    def compute_hash(self) -> str:
        body = {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "layer": self.layer.value,
            "correlation_id": self.correlation_id,
            "event_id": self.event_id,
            "confidence": self.confidence,
            "visibility": self.visibility,
            "payload_hash": self.payload_hash,
            "prev_hash": self.prev_hash,
        }
        blob = json.dumps(body, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


class AuditLog:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, output: LayerOutput) -> AuditRecord:
        prev = self._records[-1].record_hash if self._records else ""
        rec = AuditRecord(
            layer=output.layer,
            correlation_id=output.correlation_id,
            event_id=output.event_id,
            confidence=output.confidence,
            visibility=output.visibility,
            payload_hash=_hash_payload(output),
            prev_hash=prev,
        )
        rec = rec.model_copy(update={"record_hash": rec.compute_hash()})
        self._records.append(rec)
        return rec

    def verify(self) -> bool:
        prev = ""
        for r in self._records:
            if r.prev_hash != prev:
                return False
            if r.record_hash != r.compute_hash():
                return False
            prev = r.record_hash
        return True

    def __iter__(self) -> Iterator[AuditRecord]:
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)
