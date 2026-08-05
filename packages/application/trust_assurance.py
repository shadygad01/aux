"""Issue and replay deterministic recommendation trust manifests."""

from datetime import datetime
from hashlib import sha256

from packages.domain import DecisionExplanation, RecommendationTrust


class TrustAssurance:
    @staticmethod
    def issue(
        explanation: DecisionExplanation,
        confidence: int,
        uncertainty: int,
        policy_version: str,
        canonical_input: str,
        calculation_reference: str,
        audit_reference: str,
        measured_at: datetime,
    ) -> RecommendationTrust:
        if not canonical_input:
            raise ValueError("canonical replay input is required")
        return RecommendationTrust(
            explanation.decision,
            tuple(dict.fromkeys(trace.fact for trace in explanation.traces)),
            explanation.supporting_evidence,
            tuple(dict.fromkeys(trace.reasoning_reference for trace in explanation.traces)),
            explanation.weakening_evidence,
            confidence,
            uncertainty,
            policy_version,
            sha256(canonical_input.encode("utf-8")).hexdigest(),
            calculation_reference,
            audit_reference,
            measured_at,
        )

    @staticmethod
    def verifies_input(trust: RecommendationTrust, canonical_input: str) -> bool:
        fingerprint = sha256(canonical_input.encode("utf-8")).hexdigest()
        return fingerprint == trust.canonical_input_sha256
