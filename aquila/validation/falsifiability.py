"""Falsification test runner.

Runs the pytest node id declared in each ``Assumption.falsifiable_by``
in a subprocess and reports whether the assumption is empirically
falsifiable today.

Renamed from ``FalsifiabilityChecker`` to ``FalsificationTestRunner``
to be honest about what the class does: it executes tests, it does not
*check* logical falsifiability. ``FalsifiabilityChecker`` is kept as a
deprecation alias so existing imports keep working.
"""

from __future__ import annotations

import os
import subprocess
import sys
import warnings
from dataclasses import dataclass

from aquila.governance.assumptions import AssumptionRegistry


@dataclass(frozen=True)
class FalsificationResult:
    assumption: str
    node_id: str
    passed: bool
    returncode: int
    stdout: str
    stderr: str


class FalsificationTestRunner:
    """Run the pytest node id declared by each assumption.

    Empty ``falsifiable_by`` → automatic ``False`` (no test, no proof).
    Non-zero returncode (test missing, collection error, failure) → ``False``.
    """

    def __init__(self, registry: AssumptionRegistry, *, timeout: float = 120.0) -> None:
        self._reg = registry
        self._timeout = timeout

    def _run_node(self, node_id: str) -> FalsificationResult:
        if not node_id:
            return FalsificationResult(
                assumption="", node_id="", passed=False, returncode=-1,
                stdout="", stderr="empty_node_id",
            )
        cmd = [
            sys.executable, "-m", "pytest",
            "-x", "--no-header", "-q",
            "-p", "no:cacheprovider",
            node_id,
        ]
        env = os.environ.copy()
        # Prevent re-collection of the *parent* pytest run from interfering
        # by pointing PYTEST_DISABLE_PLUGIN_AUTOLOAD off; we keep it on so
        # asyncio plugins etc. still register. No flag manipulation here.
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self._timeout,
            check=False,
            env=env,
        )
        return FalsificationResult(
            assumption="",
            node_id=node_id,
            passed=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def check(self) -> dict[str, bool]:
        """Run every assumption's pytest node id and return a passed map.

        ``True`` only if (a) ``falsifiable_by`` is set, (b) pytest finds the
        node, and (c) the node passes.
        """
        results: dict[str, bool] = {}
        for a in self._reg.all():
            key = f"{a.namespace}.{a.name}"
            if not a.falsifiable_by:
                results[key] = False
                continue
            r = self._run_node(a.falsifiable_by)
            results[key] = r.passed
        return results

    def all_falsifiable(self) -> bool:
        return all(self.check().values())


class FalsifiabilityChecker(FalsificationTestRunner):
    """Deprecated alias. Will be removed in a future milestone.

    Kept for backward compatibility per HARD RULE #8.
    """

    def __init__(self, registry: AssumptionRegistry, *, timeout: float = 120.0) -> None:
        warnings.warn(
            "FalsifiabilityChecker is deprecated; use FalsificationTestRunner.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(registry, timeout=timeout)
