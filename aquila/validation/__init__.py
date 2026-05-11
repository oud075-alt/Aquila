"""Scientific validation framework.

Verifies:
- replay reproducibility
- causal integrity (DAG no-cycles)
- ontology consistency
- safety (no-signal) compliance
- audit chain integrity
- falsifiability (every assumption has a falsifier)
"""

from aquila.validation.falsifiability import FalsifiabilityChecker
from aquila.validation.suite import ValidationSuite, ValidationReport

__all__ = ["FalsifiabilityChecker", "ValidationSuite", "ValidationReport"]
