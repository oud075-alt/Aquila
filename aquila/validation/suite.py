from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.base import LayerOutput
from aquila.governance.assumptions import AssumptionRegistry
from aquila.observability.audit import AuditLog
from aquila.ontology.registry import OntologyRegistry
from aquila.protocols.compatibility import ProtocolCompatibilityMatrix
from aquila.safety import SafetyKernel
from aquila.validation.falsifiability import FalsificationTestRunner


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    audit_chain_ok: bool
    ontology_ok: bool
    safety_ok: bool
    protocol_ok: bool
    falsifiability_ok: bool
    details: dict = Field(default_factory=dict)

    @property
    def all_pass(self) -> bool:
        return all([
            self.audit_chain_ok, self.ontology_ok, self.safety_ok,
            self.protocol_ok, self.falsifiability_ok,
        ])


class ValidationSuite:
    def __init__(
        self,
        audit: AuditLog,
        ontology: OntologyRegistry,
        safety: SafetyKernel,
        protocols: ProtocolCompatibilityMatrix,
        assumptions: AssumptionRegistry,
    ) -> None:
        self._audit = audit
        self._ont = ontology
        self._safety = safety
        self._protocols = protocols
        self._falsifier = FalsificationTestRunner(assumptions)

    def run(self, outputs: dict | None = None) -> ValidationReport:
        safety_ok = True
        protocol_ok = True
        details: dict = {}
        if outputs:
            for ln, o in outputs.items():
                if isinstance(o, LayerOutput):
                    v = self._safety.check(o)
                    if not v.ok:
                        safety_ok = False
                        details.setdefault("safety_failures", []).append(
                            {"layer": ln.value, "reason": v.reason}
                        )
                    if not self._protocols.is_compatible(o):
                        protocol_ok = False
                        details.setdefault("protocol_failures", []).append(ln.value)
        return ValidationReport(
            audit_chain_ok=self._audit.verify(),
            ontology_ok=bool(self._ont.current()),
            safety_ok=safety_ok,
            protocol_ok=protocol_ok,
            falsifiability_ok=self._falsifier.all_falsifiable(),
            details=details,
        )
