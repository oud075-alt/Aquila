"""Versioned ontology registry. Closes audit gap #61."""

from __future__ import annotations

from aquila.deception.schemas import DeceptionKind
from aquila.ontology.liquidity import LIQUIDITY_ONTOLOGY
from aquila.ontology.schemas import OntologyEntry, OntologySnapshot
from aquila.pathology.schemas import PathologyKind
from aquila.regime.schemas import RegimeKind
from aquila.structural.schemas import StructuralState


class OntologyRegistry:
    def __init__(self) -> None:
        self._snapshots: list[OntologySnapshot] = []
        self._publish_initial()

    def _publish_initial(self) -> None:
        entries: list[OntologyEntry] = []
        for s in StructuralState:
            entries.append(OntologyEntry(namespace="structural", name=s.value, description=s.value))
        for p in PathologyKind:
            entries.append(OntologyEntry(namespace="pathology", name=p.value, description=p.value))
        for d in DeceptionKind:
            entries.append(OntologyEntry(namespace="deception", name=d.value, description=d.value))
        for r in RegimeKind:
            entries.append(OntologyEntry(namespace="regime", name=r.value, description=r.value))
        entries.extend(LIQUIDITY_ONTOLOGY)
        self._snapshots.append(OntologySnapshot(entries=entries, version="1.0.0"))

    def current(self) -> OntologySnapshot:
        return self._snapshots[-1]

    def history(self) -> list[OntologySnapshot]:
        return list(self._snapshots)

    def publish(self, snap: OntologySnapshot) -> None:
        self._snapshots.append(snap)
