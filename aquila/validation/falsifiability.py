from __future__ import annotations

from aquila.governance.assumptions import AssumptionRegistry


class FalsifiabilityChecker:
    def __init__(self, registry: AssumptionRegistry) -> None:
        self._reg = registry

    def check(self) -> dict[str, bool]:
        return {f"{a.namespace}.{a.name}": bool(a.falsifiable_by) for a in self._reg.all()}

    def all_falsifiable(self) -> bool:
        return all(self.check().values())
