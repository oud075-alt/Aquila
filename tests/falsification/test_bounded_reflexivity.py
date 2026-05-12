"""Falsification test for Assumption ``meta.bounded_reflexivity``.

Claim: meta-cognition recursion depth must remain <= 1. If
``assert_within_bound`` ever accepts depth > 1, the bound is broken and
the meta layer can loop on its own outputs.
"""

from __future__ import annotations

import pytest

from aquila.meta.reflexivity import (
    MAX_REFLEXIVE_DEPTH,
    ReflexivityViolation,
    assert_within_bound,
)


def test_meta_depth_above_one_raises():
    assert MAX_REFLEXIVE_DEPTH == 1
    assert_within_bound(0)
    assert_within_bound(1)
    with pytest.raises(ReflexivityViolation):
        assert_within_bound(2)
    with pytest.raises(ReflexivityViolation):
        assert_within_bound(5)
