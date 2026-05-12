"""Append-only outcome store.

JSONL-backed. Lives entirely outside the cognition flow. ``OutcomeStore``
must never be referenced from any orchestrator / layer that runs
forward in time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from aquila.outcomes.schemas import ForwardOutcome


class OutcomeStore:
    """In-memory + optional JSONL append-only store."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[ForwardOutcome] = []
        self._path = Path(path) if path else None
        if self._path and self._path.exists():
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    self._records.append(ForwardOutcome.model_validate_json(line))

    def append(self, outcome: ForwardOutcome) -> None:
        self._records.append(outcome)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(outcome.model_dump_json())
                f.write("\n")

    def get(self, trigger_event_id: str) -> ForwardOutcome | None:
        for r in self._records:
            if r.trigger_event_id == trigger_event_id:
                return r
        return None

    def all(self) -> list[ForwardOutcome]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[ForwardOutcome]:
        return iter(self._records)
