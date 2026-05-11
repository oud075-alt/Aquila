"""Fingerprint extractor — turns structural+pathology into a comparable vector."""

from __future__ import annotations

from aquila.core.numeric import safe_float
from aquila.memory.schemas import EpisodeFingerprint
from aquila.pathology.schemas import PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis, StructuralState

_STATE_ORDER = list(StructuralState)


class FingerprintExtractor:
    def extract(
        self,
        diag: StructuralDiagnosis,
        report: PathologyReport,
        snap: PrimitiveSnapshot | None,
    ) -> EpisodeFingerprint:
        # one-hot for structural state
        oh = [1.0 if diag.state == s else 0.0 for s in _STATE_ORDER]
        vec: list[float] = list(oh)
        vec.append(safe_float(diag.score))
        vec.append(safe_float(report.aggregate_pathology_score))
        vec.append(safe_float(report.aggregate_contradiction_score))
        if snap is not None:
            vec.extend([
                safe_float(snap.realized_vol),
                safe_float(snap.return_pct),
                safe_float(snap.range_pct),
                safe_float(snap.body_ratio),
                safe_float(snap.upper_wick_ratio),
                safe_float(snap.lower_wick_ratio),
                safe_float(snap.volume_z),
            ])
        else:
            vec.extend([0.0] * 7)

        tags = [f"state:{diag.state.value}"]
        if diag.secondary_state:
            tags.append(f"sec:{diag.secondary_state.value}")
        for sig in report.signatures:
            tags.append(f"path:{sig.kind.value}")
        return EpisodeFingerprint(vector=vec, tags=tags)
