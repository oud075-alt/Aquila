"""Forward outcomes module.

Stores realised, lookahead-safe outcomes for triggers emitted by
detectors. Deliberately decoupled from the orchestrator and the memory
archive so that no lookahead can leak into live cognition.

Public API:

- ``ForwardOutcome``    — frozen outcome record
- ``OutcomeEnricher``   — attaches forward outcomes to trigger events
- ``OutcomeStore``      — append-only outcome store
- ``LookaheadError``    — raised when the enricher is asked to evaluate
                           an outcome from a bar that is not strictly
                           after the trigger timestamp
"""

from aquila.outcomes.enricher import LookaheadError, OutcomeEnricher
from aquila.outcomes.schemas import ForwardOutcome
from aquila.outcomes.store import OutcomeStore

__all__ = [
    "ForwardOutcome",
    "OutcomeEnricher",
    "OutcomeStore",
    "LookaheadError",
]
