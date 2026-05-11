"""Cognitive failure-state framework.

States:
- normal
- degraded_cognition
- uncertainty_overflow
- contradiction_saturation
- low_visibility_lockdown
- instability_escalation

Driven by L8 outputs + drift monitor.
"""

from aquila.failure.detector import FailureStateDetector
from aquila.failure.load_shed import LoadShedPolicy
from aquila.failure.schemas import FailureState, FailureStateReport

__all__ = ["FailureStateDetector", "LoadShedPolicy", "FailureState", "FailureStateReport"]
