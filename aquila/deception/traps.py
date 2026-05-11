"""Bull / bear trap detectors. Structural-only — no signal output."""

from __future__ import annotations

from aquila.core.numeric import safe_prob
from aquila.core.types import Severity
from aquila.deception.interfaces import TrapDetector
from aquila.deception.schemas import DeceptionKind, TrapSignature
from aquila.pathology.schemas import PathologyKind, PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis, StructuralState


def _sev(p: float) -> Severity:
    if p >= 0.8:
        return Severity.CRITICAL
    if p >= 0.6:
        return Severity.HIGH
    if p >= 0.4:
        return Severity.MODERATE
    if p >= 0.2:
        return Severity.LOW
    return Severity.NIL


class StructuralTrapDetector(TrapDetector):
    def detect(
        self,
        *,
        structural: StructuralDiagnosis,
        pathology: PathologyReport,
        primitives: PrimitiveSnapshot | None,
    ) -> list[TrapSignature]:
        out: list[TrapSignature] = []
        if primitives is None:
            return out

        path_kinds = {s.kind for s in pathology.signatures}

        # Bull trap: displacement up immediately followed by absorption + upper-wick dominance
        if (
            structural.state in (StructuralState.DISPLACEMENT, StructuralState.TREND_UP)
            and primitives.return_pct > 0
            and primitives.upper_wick_ratio >= 0.55
            and (PathologyKind.ABSORPTION_ON_DISPLACEMENT in path_kinds or primitives.volume_z > 1.0)
        ):
            p = safe_prob(0.5 + 0.3 * primitives.upper_wick_ratio)
            out.append(TrapSignature(
                kind=DeceptionKind.BULL_TRAP, probability=p, severity=_sev(p),
                rationale="upward displacement with absorption + upper-wick rejection",
            ))

        # Bear trap: same logic mirrored
        if (
            structural.state in (StructuralState.DISPLACEMENT, StructuralState.TREND_DOWN)
            and primitives.return_pct < 0
            and primitives.lower_wick_ratio >= 0.55
            and (PathologyKind.ABSORPTION_ON_DISPLACEMENT in path_kinds or primitives.volume_z > 1.0)
        ):
            p = safe_prob(0.5 + 0.3 * primitives.lower_wick_ratio)
            out.append(TrapSignature(
                kind=DeceptionKind.BEAR_TRAP, probability=p, severity=_sev(p),
                rationale="downward displacement with absorption + lower-wick rejection",
            ))

        # False continuation: expansion w/o volume
        if PathologyKind.EXPANSION_WITHOUT_VOLUME in path_kinds:
            p = 0.55
            out.append(TrapSignature(
                kind=DeceptionKind.FALSE_CONTINUATION, probability=p, severity=_sev(p),
                rationale="expansion without confirming volume",
            ))

        return out
