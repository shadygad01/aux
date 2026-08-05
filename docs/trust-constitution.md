# Trust

Trust is produced by verification, not by a score or a claim of intelligence. `OfficialDecision
3.0` requires a `RecommendationTrust` manifest in addition to its complete explanation and
pre-publication critique.

The manifest exposes facts, evidence references, reasoning references, contradictions, confidence,
uncertainty, policy version, calculation reference, audit reference, measurement time, and a
SHA-256 fingerprint of the exact canonical input bundle. Replaying the same canonical bytes must
produce the same fingerprint; altered input fails verification.

Decision authorization rejects a trust recommendation that differs from reasoning, confidence that
does not reproduce reasoning reliability, or facts that do not resolve through the explanation
tree. Empty facts, evidence, reasoning, or contradictions are invalid. A reviewed absence must be
stated explicitly rather than hidden in an empty collection.

Canonicalization is part of the contract: production must use a versioned serializer and include
all evidence values, freshness, sources, knowledge revisions, policy/configuration versions, market
snapshot, code/model version, and calculation inputs. Anything absent from that bundle must not
influence the recommendation.

The manifest makes tampering detectable; it does not itself prove source truth. Production still
requires durable content-addressed artifacts, signature/identity verification, access control, and
an independent replay tool.
