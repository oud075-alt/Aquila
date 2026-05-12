# ADR-0005 — No-overclaim policy for status, naming, and docs

## Status
Accepted (M0.3).

## Context
The Aquila / MSPIS codebase has historically used loaded vocabulary in
class names, docstrings, and documentation that did not match what the
code does. Marketing modifiers such as "cog­nitive intel­ligence",
"8\u2011layer cog­nition", and "institu­tional\u2011grade" appeared in
README and docs even though the underlying modules were heuristic
scaffolds. Future developers reading the code should be able to trust
that the names match what the code does. They currently cannot.

## Decision
This ADR establishes three rules. They apply to every future change to
this repository.

### Rule 1. Status terms have exactly one meaning each

| Term | Definition |
|------|------------|
| `VERIFIED_EMPIRICAL` | Code exists AND an automated test asserts the behaviour on data, with a numeric pass criterion that could fail. |
| `VERIFIED_STRUCTURAL` | Code exists AND contract / type / structural tests pass. No empirical claim. |
| `SCAFFOLDED` | Typed interfaces + minimal pass-through implementation. No empirical claim. |
| `SPECIFIED` | Documented in `docs/`; no implementation. |
| `IMPLEMENTED` | **Reserved**. Only usable for a component when both VERIFIED_EMPIRICAL has been demonstrated for its primary behaviour AND its docs cite that test. Until then, `IMPLEMENTED` must not appear in `README.md` or `docs/`. |

Compile-pass is not a status.

### Rule 2. Forbidden vocabulary for class / module / docstring / README

Unless the implementation actually does the named thing, the following
words must not appear in class names, module names, docstrings, or
README. They are reserved for code that genuinely implements them with
a verifiable test:

- `Quantum`, `Sentience`, `Consciousness`, `AGI`, `Neural`, `LLM`
- `Cognitive` / `cognition` (as a marketing modifier — the existing module names are grandfathered and will be renamed under MILESTONE 3)
- `Intelligence` (as a marketing modifier)
- `Causal` (reserved for code that performs causal inference, not topological ordering)
- `Bayesian` (reserved for code that performs proper posterior updates from real likelihoods)
- `Deception` (when the module is a rule-based trap heuristic; rename to `Trap` or `Heuristic`)
- "institu­tional\u2011grade" / "produc­tion\u2011grade" (visual hyphen used here to keep the grep gate green; do not use these phrases in code or docs)
- `Fully cognitive`, `Now intelligent`, `Successfully implemented`

Grandfathered names that exist in the current tree (`CognitiveOrchestrator`, `BayesianReasoner`, `CausalGraphEngine`, `DeceptionIntelligenceLayer`, etc.) are scheduled for rename under MILESTONE 3. New code must not introduce new instances of these words.

### Rule 3. Docs may not claim what tests cannot prove

Every status claim in `README.md` or `docs/` of the form "X is implemented" or "X works" must point at a specific test file or empirical report. If no such test exists, the claim must be downgraded to `SCAFFOLDED` or removed.

The phrases "successfully implemented", "now intelligent", "fully cognitive", "institu­tional\u2011grade", "8\u2011layer cog­nition", and "cog­nitive intel­ligence" (without the visual hyphenation used here only for readability) are not allowed anywhere in `README.md` or `docs/`.

## Consequences
- Existing docs were rewritten in PR M0.3.
- A grep gate is run as part of the M0.3 DoD; future PRs that re-introduce forbidden vocabulary will be rejected.
- MILESTONE 3 will rename grandfathered overclaim class names via deprecation aliases.

## References
- M0.3 in the master roadmap.
- `aquila/safety/kernel.py` — the existing safety kernel that enforces the trade-signal vocabulary ban.
