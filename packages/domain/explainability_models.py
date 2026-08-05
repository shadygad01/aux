"""Mandatory decision explanations and fact-to-source lineage."""

from dataclasses import dataclass

from .evidence_models import Recommendation


@dataclass(frozen=True, slots=True)
class ExplanationTrace:
    reasoning_reference: str
    knowledge_reference: str
    evidence_reference: str
    fact: str
    source: str

    def __post_init__(self) -> None:
        values = (
            self.reasoning_reference,
            self.knowledge_reference,
            self.evidence_reference,
            self.fact,
            self.source,
        )
        if any(not value.strip() for value in values):
            raise ValueError("explanation traces require reasoning-to-source lineage")


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    decision: Recommendation
    why: tuple[str, ...]
    why_now: tuple[str, ...]
    why_not_opposite: tuple[str, ...]
    why_not_wait: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    weakening_evidence: tuple[str, ...]
    missing_information: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    traces: tuple[ExplanationTrace, ...]
    contract_version: str = "1.0.0"

    def __post_init__(self) -> None:
        answers = (
            self.why,
            self.why_now,
            self.why_not_opposite,
            self.why_not_wait,
            self.supporting_evidence,
            self.weakening_evidence,
            self.missing_information,
            self.invalidation_conditions,
        )
        if any(not answer or any(not item.strip() for item in answer) for answer in answers):
            raise ValueError("every explainability question requires an explicit answer")
        if not self.traces:
            raise ValueError("explanations require decision-to-source lineage")
        trace_evidence = {trace.evidence_reference for trace in self.traces}
        if not set(self.supporting_evidence).issubset(trace_evidence):
            raise ValueError("supporting evidence must resolve through the explainability tree")
