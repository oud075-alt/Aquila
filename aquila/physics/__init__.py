"""Structural state-transition physics engine.

Detects: probabilistic transitions, unstable transitions, transition
acceleration, regime-collapse dynamics. Built on top of L7's
`RegimeTransitionGraph` for the regime layer; this module exposes a
state-level (structural-state) version used by upstream analytics.
"""

from aquila.physics.engine import StateTransitionPhysics
from aquila.physics.schemas import PhysicsReport, TransitionVelocity

__all__ = ["StateTransitionPhysics", "PhysicsReport", "TransitionVelocity"]
