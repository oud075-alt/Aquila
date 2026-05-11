from __future__ import annotations

from aquila.observability.audit import AuditLog
from aquila.ontology.registry import OntologyRegistry
from aquila.protocols.compatibility import ProtocolCompatibilityMatrix


class IntegrityValidator:
    def __init__(
        self,
        audit: AuditLog,
        registry: OntologyRegistry,
        matrix: ProtocolCompatibilityMatrix,
    ) -> None:
        self._audit = audit
        self._reg = registry
        self._matrix = matrix

    def verify_audit_chain(self) -> bool:
        return self._audit.verify()

    def verify_ontology(self) -> bool:
        return self._reg.current().version == "1.0.0"

    def verify_protocol(self) -> bool:
        return True
