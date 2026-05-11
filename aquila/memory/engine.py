"""Layer 4 engine — Episodic Memory cognitive layer."""

from __future__ import annotations

from aquila.core.base import CognitiveLayer, LayerContext, LayerOutput
from aquila.core.types import LayerName
from aquila.memory.archive import RegimeArchive
from aquila.memory.fingerprint import FingerprintExtractor
from aquila.memory.index import SimpleSimilarityIndex
from aquila.memory.interfaces import MemoryStore, SimilarityIndex
from aquila.memory.recall import sequence_match
from aquila.memory.schemas import (
    EpisodeRecord,
    MemoryQuery,
    MemoryRecall,
)
from aquila.memory.store import InMemoryStore
from aquila.pathology.schemas import PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis


class EpisodicMemoryLayer(CognitiveLayer[PathologyReport, MemoryRecall]):
    layer_name = LayerName.MEMORY

    def __init__(
        self,
        store: MemoryStore | None = None,
        index: SimilarityIndex | None = None,
        extractor: FingerprintExtractor | None = None,
        write_on_real: bool = True,
        sequence_n: int = 3,
        top_k: int = 5,
    ) -> None:
        super().__init__()
        self._archive = RegimeArchive(store or InMemoryStore())
        self._index = index or SimpleSimilarityIndex()
        self._extractor = extractor or FingerprintExtractor()
        self._write_on_real = write_on_real
        self._sequence_n = sequence_n
        self._top_k = top_k
        self._state_history: list[str] = []

    def process(
        self, payload: PathologyReport, ctx: LayerContext
    ) -> LayerOutput[MemoryRecall]:
        struct_out = ctx.upstream_outputs.get(LayerName.STRUCTURAL)
        prim_out = ctx.upstream_outputs.get(LayerName.PRIMITIVES)
        if struct_out is None:
            empty = MemoryRecall(archive_size=self._archive.size())
            return self.wrap(payload=empty, ctx=ctx, confidence=0.0, visibility="degraded")

        diag: StructuralDiagnosis = struct_out.payload  # type: ignore[assignment]
        snap: PrimitiveSnapshot | None = prim_out.payload if prim_out else None  # type: ignore[assignment]

        fp = self._extractor.extract(diag, payload, snap)
        query = MemoryQuery(fingerprint=fp, symbol=ctx.symbol, top_k=self._top_k)
        analogs = self._index.search(query, self._archive.all())

        self._state_history.append(diag.state.value)
        if len(self._state_history) > 256:
            self._state_history = self._state_history[-256:]
        seq = sequence_match(self._state_history, self._archive.all(), n=self._sequence_n)

        # Write current episode (skip synthetic / replay-write-disabled paths)
        written = False
        if self._write_on_real and ctx.origin == "real":
            rec = EpisodeRecord(
                symbol=ctx.symbol,
                timestamp=ctx.now(),
                diagnosis=diag,
                pathology=payload,
                fingerprint=fp,
                origin=ctx.origin,
            )
            self._archive.append(rec)
            written = True

        recall = MemoryRecall(
            analogs=analogs,
            sequence_match=seq,
            archive_size=self._archive.size(),
            written=written,
            correlated_event_id=struct_out.event_id,
        )

        if analogs:
            confidence = max(a.similarity for a in analogs)
        else:
            confidence = 0.0

        visibility = "full" if self._archive.size() >= 10 else "partial"
        return self.wrap(
            payload=recall,
            ctx=ctx,
            confidence=confidence,
            visibility=visibility,
            evidence=[struct_out.as_ref()],
        )

    @property
    def archive(self) -> RegimeArchive:
        return self._archive
