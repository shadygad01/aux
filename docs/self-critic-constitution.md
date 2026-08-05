# Self-Critic

Self-Critic is an independent Learning Capability workflow. It does not edit the original decision,
reasoning, confidence, or outcome. It appends a challenge tied to an exact Decision Memory version.

Every critique answers what was ignored, overweighted, and underweighted; whether uncertainty was
underestimated; what conflicts existed; and what an alternative reasoning path would produce.
Every answer is mandatory and must carry evidence references. “None found” is permitted only as an
explicit reviewed conclusion, never as an empty field.

Official Decision 2.0 requires a matching `PRE_PUBLICATION` critique, making an unchallenged new
official output unpublishable. Later `OUTCOME_REVIEW` critiques question both winning and failed
decisions. A win creates no correctness claim and does not promote knowledge.

Every `LOSING` or `FALSE_POSITIVE` outcome automatically creates an open Research Task asking why
the decision passed its evidence and uncertainty gates. Task completion remains governed research;
it cannot directly change production behavior.

The included repository is append-only and in-memory for composition and tests. Continuous
production operation still requires durable storage, a scheduler that detects unreviewed decision
versions, retry/idempotency controls, and monitoring for critique backlog age. Until those adapters
exist, continuous self-criticism must not be claimed.
