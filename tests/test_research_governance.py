import unittest
from datetime import UTC, datetime

from capabilities.research import ResearchCapability
from packages.application import ResearchGovernance
from packages.domain import EdgeStatistics, LearningConfidence, LearningRecord, ResearchOutputStatus
from packages.infrastructure import InMemoryCapabilityTelemetry, InMemoryResearchProposalArchive

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def statistics() -> EdgeStatistics:
    confidence = LearningConfidence(0.6, 0.7, 0.8, 0.9, 0.75)
    return EdgeStatistics(("discount", "sweep"), 100, 60, 40, 0.6, confidence)


class FakeResearchEvaluator:
    def evaluate_edge(
        self,
        records: tuple[LearningRecord, ...],
        evidence_combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics:
        return statistics()


class ResearchGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.archive = InMemoryResearchProposalArchive()
        self.service = ResearchGovernance(self.archive)

    def test_proposal_contains_every_field_and_is_never_production(self) -> None:
        proposal = self.service.propose(
            "proposal-1",
            "Do discount sweeps behave differently in London?",
            "London discount sweeps have a repeatable positive edge.",
            "Walk-forward regime-stratified event study.",
            ("dataset:1", "decision-memory:cohort:1"),
            statistics(),
            "Regime selection and multiple-testing bias.",
            "Higher precision without increasing trade frequency.",
            "Would require a separately governed Level 2 rule proposal.",
            NOW,
        )
        self.assertEqual(proposal.status, ResearchOutputStatus.PROPOSAL)
        self.assertFalse(proposal.production_eligible)
        self.assertEqual(self.archive.proposals, [proposal])

    def test_missing_method_or_evidence_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "every governed field"):
            self.service.propose(
                "proposal-2",
                "Question",
                "Hypothesis",
                "",
                (),
                statistics(),
                "Risk",
                "Gain",
                "Migration",
                NOW,
            )

    def test_research_capability_routes_through_governance(self) -> None:
        capability = ResearchCapability(
            FakeResearchEvaluator(),
            InMemoryCapabilityTelemetry(),
            proposal_service=self.service,
        )
        proposal = capability.propose(
            "proposal-3",
            "Question",
            "Hypothesis",
            "Method",
            statistics(),
            ("evidence:1",),
            "Risk",
            "Gain",
            "Migration impact",
            NOW,
        )
        self.assertFalse(proposal.production_eligible)


if __name__ == "__main__":
    unittest.main()
