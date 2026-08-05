import unittest
from datetime import UTC, datetime

from packages.application import InstitutionalComprehensionGate
from packages.domain import (
    ComprehensionVerdict,
    ExplainedConcept,
    ExplainedStatistic,
    ReasoningComprehensionReview,
    ReasoningDecision,
    ReasoningStage,
    Recommendation,
    StageReasoning,
    StageStatus,
)
from packages.infrastructure import InMemoryComprehensionAudit

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def reasoning() -> ReasoningDecision:
    stages = tuple(
        StageReasoning(stage, StageStatus.COMPLETE, "Reviewed.", ()) for stage in ReasoningStage
    )
    return ReasoningDecision(
        "reasoning-1",
        Recommendation.WAIT,
        65,
        70,
        "Evidence is incomplete.",
        ("Macro context is mixed.",),
        ("evidence:1",),
        ("evidence:2",),
        ("Liquidity confirmation",),
        ("Range continuation",),
        (),
        ("Fresh expansion invalidates WAIT.",),
        ("Add liquidity confirmation.",),
        stages,
        NOW,
        "policy",
        "4.0.0",
    )


class ComprehensionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = InMemoryComprehensionAudit()
        self.gate = InstitutionalComprehensionGate(self.audit, "comprehension-v1")

    def test_professional_plain_language_review_is_approved(self) -> None:
        review = self.gate.review(
            reasoning(),
            "Macro evidence is mixed and liquidity confirmation is absent, so WAIT remains.",
            (ExplainedConcept("Expansion", "Price is moving away from its prior balance area."),),
            (
                ExplainedStatistic(
                    "Quality 65", "The reviewed setup earned 65 of 100 points.", "calc:1"
                ),
            ),
            (),
            "The trader must judge execution quality if confirmation later appears.",
            "Gold Brain does not select entries or execute trades.",
            "institutional-trader-review",
            ("reasoning:1", "calc:1"),
            NOW,
        )
        self.assertEqual(review.verdict, ComprehensionVerdict.APPROVED)

    def test_opaque_reasoning_is_recorded_as_rejected(self) -> None:
        review = self.gate.review(
            reasoning(),
            "The recommendation cannot yet be translated into trading terms.",
            (),
            (),
            ("Latent factor embedding has no trader-facing meaning.",),
            "Trader judgment cannot be applied until the factor is explained.",
            "Opaque factors cannot influence production.",
            "reviewer",
            ("reasoning:1",),
            NOW,
        )
        self.assertEqual(review.verdict, ComprehensionVerdict.REJECTED)

    def test_approved_review_requires_explained_concepts_and_statistics(self) -> None:
        with self.assertRaisesRegex(ValueError, "explain abstractions"):
            ReasoningComprehensionReview(
                "review-1",
                "reasoning-1",
                ComprehensionVerdict.APPROVED,
                "Plain summary.",
                (),
                (),
                (),
                "Trader judgment remains required.",
                "No execution automation.",
                "reviewer",
                ("reasoning:1",),
                NOW,
                "policy",
            )

    def test_malformed_explanations_and_opaque_approval_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "plain-language"):
            ExplainedConcept("Expansion", "")
        with self.assertRaisesRegex(ValueError, "reproducible calculation"):
            ExplainedStatistic("Quality 65", "Meaning", "")
        with self.assertRaisesRegex(ValueError, "opaque"):
            ReasoningComprehensionReview(
                "review-opaque",
                "reasoning-1",
                ComprehensionVerdict.APPROVED,
                "Summary",
                (ExplainedConcept("Term", "Meaning"),),
                (ExplainedStatistic("Claim", "Meaning", "calc:1"),),
                ("Hidden factor",),
                "Trader judgment",
                "No execution",
                "reviewer",
                ("reasoning:1",),
                NOW,
                "policy",
            )

    def test_review_lifecycle_and_audit_are_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "policy version"):
            InstitutionalComprehensionGate(self.audit, "")
        approved = self.gate.review(
            reasoning(),
            "Plain summary.",
            (ExplainedConcept("Term", "Meaning"),),
            (ExplainedStatistic("Claim", "Meaning", "calc:1"),),
            (),
            "Trader judgment remains.",
            "No execution.",
            "reviewer",
            ("reasoning:1",),
            NOW,
        )
        self.assertEqual(approved.verdict, ComprehensionVerdict.APPROVED)
        with self.assertRaisesRegex(ValueError, "already reviewed"):
            self.audit.append(approved)
        with self.assertRaisesRegex(ValueError, "timestamp"):
            ReasoningComprehensionReview(
                "review-naive",
                "reasoning-2",
                ComprehensionVerdict.REJECTED,
                "Summary",
                (),
                (),
                ("Opaque",),
                "Trader judgment",
                "No execution",
                "reviewer",
                ("reasoning:2",),
                datetime(2026, 8, 5),
                "policy",
            )


if __name__ == "__main__":
    unittest.main()
