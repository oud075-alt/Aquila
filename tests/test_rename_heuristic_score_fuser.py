"""Migration tests for the BayesianReasoner → HeuristicScoreFuser rename (M3.1).

These tests assert ONLY the rename contract:

- new name exists and works;
- new name's output is identical to the legacy name's output;
- legacy name still importable (HARD RULE #8);
- legacy name emits ``DeprecationWarning`` on any attribute access.

They do NOT assert anything about Bayesian semantics, because the code
deliberately does not implement Bayesian semantics. See ADR-0006.
"""

from __future__ import annotations

import warnings

from aquila.probabilistic import BayesianReasoner, Evidence, HeuristicScoreFuser


def _ev() -> list[Evidence]:
    return [
        Evidence(name="a", likelihood=0.7, weight=2.0),
        Evidence(name="b", likelihood=0.3, weight=1.0),
    ]


def test_new_name_exists_and_returns_belief():
    pb = HeuristicScoreFuser.fuse("hyp", prior=0.4, evidence=_ev())
    assert 0.0 <= pb.posterior <= 1.0
    assert pb.hypothesis == "hyp"
    assert pb.prior == 0.4


def test_legacy_name_still_importable():
    assert BayesianReasoner is not None


def test_legacy_name_emits_deprecation_warning_on_access():
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        _ = BayesianReasoner.fuse
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "BayesianReasoner is deprecated" in str(w.message)
        for w in records
    ), f"expected DeprecationWarning, got: {[str(w.message) for w in records]}"


def test_legacy_update_method_still_works_as_alias():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        new_pb = HeuristicScoreFuser.fuse("h", prior=0.2, evidence=_ev())
        old_pb = BayesianReasoner.update("h", prior=0.2, evidence=_ev())
    assert new_pb.posterior == old_pb.posterior
    assert new_pb.prior == old_pb.prior


def test_empty_evidence_returns_prior_as_posterior():
    pb = HeuristicScoreFuser.fuse("h", prior=0.3, evidence=[])
    assert pb.posterior == 0.3
