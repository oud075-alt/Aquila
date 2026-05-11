"""Memory stores. Closes audit gap #5."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Iterable

from aquila.core.exceptions import MemoryStoreError
from aquila.memory.interfaces import MemoryStore
from aquila.memory.schemas import EpisodeRecord


class InMemoryStore(MemoryStore):
    def __init__(self, capacity: int = 10000) -> None:
        self._buf: deque[EpisodeRecord] = deque(maxlen=capacity)

    def append(self, record: EpisodeRecord) -> None:
        self._buf.append(record)

    def all(self) -> Iterable[EpisodeRecord]:
        return list(self._buf)

    def size(self) -> int:
        return len(self._buf)


class JsonlStore(MemoryStore):
    """Append-only JSONL store. Provides minimal durability without
    pulling a DB dependency. Replay safety: records are written with
    `origin` tag so replay/synthetic events never contaminate real recall.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)

    def append(self, record: EpisodeRecord) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")
        except OSError as e:  # pragma: no cover
            raise MemoryStoreError(str(e)) from e

    def all(self) -> Iterable[EpisodeRecord]:
        out: list[EpisodeRecord] = []
        if not self._path.exists():
            return out
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                out.append(EpisodeRecord.model_validate(json.loads(line)))
        return out

    def size(self) -> int:
        if not self._path.exists():
            return 0
        with self._path.open("r", encoding="utf-8") as f:
            return sum(1 for ln in f if ln.strip())
