"""Bounded reflexivity. Closes audit gap #50.

Meta-cognition evaluates other layers. To avoid an infinite reflexive
stack, this module fixes the recursion bound: meta does NOT evaluate itself.
A higher-order policy can run a *sanity check* over meta's outputs (depth 1
only); deeper meta is rejected.
"""

from __future__ import annotations

MAX_REFLEXIVE_DEPTH: int = 1


class ReflexivityViolation(Exception):
    pass


def assert_within_bound(depth: int) -> None:
    if depth > MAX_REFLEXIVE_DEPTH:
        raise ReflexivityViolation(
            f"Reflexive meta depth {depth} exceeds bound {MAX_REFLEXIVE_DEPTH}"
        )
