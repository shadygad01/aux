# Explainability

Scores are navigation aids, not reasons to trust a decision. `OfficialDecision 2.0` cannot be
created through the Decision Capability without a complete `DecisionExplanation` whose decision
matches the nine-stage reasoning output.

Every explanation explicitly answers why, why now, why not the opposite direction, why not WAIT,
supporting evidence, weakening evidence, missing information, and invalidation conditions. Empty
answers are invalid. If a category has no known item, the answer must state that reviewed absence
explicitly; callers may not hide it with an empty collection.

## Explainability tree

Each supporting evidence identifier must resolve through at least one immutable trace:

`Decision → Reasoning reference → Knowledge reference → Evidence reference → Fact → Source`

The trace stores references rather than copied claims so the user can inspect provenance. A source
label alone is not sufficient production provenance: adapters should use stable source IDs or URLs
that resolve to collection metadata and timestamps.

Publishing accepts only `OfficialDecision`; its version 2 explanation object is structurally
mandatory. The prior `official-decision-v1` schema is retained only for archived compatibility and
must not be used for new publication.
