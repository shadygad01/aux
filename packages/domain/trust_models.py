"""Verifiable recommendation facts, lineage, measurements, and replay metadata."""

from dataclasses import dataclass
from datetime import datetime

from .evidence_models import Recommendation


@dataclass(frozen=True, slots=True)
class RecommendationTrust:
    recommendation: Recommendation
    facts: tuple[str, ...]
    evidence_references: tuple[str, ...]
    reasoning_references: tuple[str, ...]
    contradictions: tuple[str, ...]
    confidence: int
    uncertainty: int
    policy_version: str
    canonical_input_sha256: str
    calculation_reference: str
    audit_reference: str
    measured_at: datetime
    contract_version: str = "1.0.0"

    def __post_init__(self) -> None:
        collections = (
            self.facts,
            self.evidence_references,
            self.reasoning_references,
            self.contradictions,
        )
        if any(not values or any(not item.strip() for item in values) for values in collections):
            raise ValueError("trust manifest fields must be explicit and non-empty")
        if not 0 <= self.confidence <= 100 or not 0 <= self.uncertainty <= 100:
            raise ValueError("trust confidence and uncertainty must be between zero and 100")
        if len(self.canonical_input_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.canonical_input_sha256
        ):
            raise ValueError("trust manifest requires a lowercase SHA-256 input fingerprint")
        values = (self.policy_version, self.calculation_reference, self.audit_reference)
        if any(not value.strip() for value in values) or self.measured_at.tzinfo is None:
            raise ValueError("trust manifest requires policy, calculation, audit, and time")
