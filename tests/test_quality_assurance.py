import json
import unittest
from datetime import UTC, datetime
from pathlib import Path

from packages.application import InstitutionalQualityGate
from packages.domain import (
    ReviewArea,
    ReviewVerdict,
    SprintReview,
    SynchronizationEvidence,
)
from packages.infrastructure import InMemoryQualityAudit

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


def reviews(verdict: ReviewVerdict = ReviewVerdict.APPROVED) -> tuple[SprintReview, ...]:
    return tuple(
        SprintReview(
            area,
            verdict,
            f"reviewer:{area.value}",
            ("Reviewed with no unresolved blocking findings.",),
            (f"evidence:{area.value}",),
            NOW,
        )
        for area in ReviewArea
    )


def synchronization(tests: bool = True) -> SynchronizationEvidence:
    return SynchronizationEvidence(
        True,
        tests,
        True,
        ("docs:diff-review",),
        ("tests:quality-run",) if tests else (),
        ("architecture:test-run",),
    )


class InstitutionalQualityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = InMemoryQualityAudit()
        self.gate = InstitutionalQualityGate(self.audit, "quality-v1")

    def test_all_ten_reviews_and_synchronization_complete_sprint(self) -> None:
        completion = self.gate.complete("SPRINT-1", reviews(), synchronization(), NOW)
        self.assertEqual(len(completion.reviews), 10)
        self.assertEqual(self.audit.completions, [completion])

    def test_missing_or_failed_review_blocks_completion(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly ten"):
            self.gate.complete("SPRINT-2", reviews()[:-1], synchronization(), NOW)
        with self.assertRaisesRegex(ValueError, "require changes"):
            self.gate.complete(
                "SPRINT-3", reviews(ReviewVerdict.CHANGES_REQUIRED), synchronization(), NOW
            )

    def test_unsynchronized_tests_block_completion(self) -> None:
        with self.assertRaisesRegex(ValueError, "remain synchronized"):
            self.gate.complete("SPRINT-4", reviews(), synchronization(False), NOW)

    def test_every_published_schema_is_documented_in_contract_catalog(self) -> None:
        catalog = (ROOT / "contracts" / "README.md").read_text(encoding="utf-8")
        undocumented = [
            path.name
            for path in (ROOT / "contracts").glob("*.schema.json")
            if path.name not in catalog
        ]
        self.assertEqual(undocumented, [])

    def test_project_readiness_is_derived_from_every_canonical_capability(self) -> None:
        history = json.loads((ROOT / "docs" / "readiness-history.json").read_text(encoding="utf-8"))
        expected = {
            "CONTEXT",
            "EXECUTION_READINESS",
            "MACRO",
            "MARKET_STORY",
            "COLLECTION",
            "NORMALIZATION",
            "EVIDENCE",
            "KNOWLEDGE",
            "REASONING",
            "DECISION",
            "LEARNING",
            "RESEARCH",
            "PUBLISHING",
            "MONITORING",
        }
        self.assertGreaterEqual(len(history["snapshots"]), 1)
        for snapshot in history["snapshots"]:
            records = snapshot["records"]
            capabilities = {record["capability"] for record in records}
            scores = [record["score"] for record in records]
            self.assertEqual(capabilities, expected)
            self.assertEqual(len(records), len(expected))
            self.assertTrue(set(scores) <= {0, 20, 40, 60, 80, 100})
            self.assertEqual(snapshot["project_score"], min(scores))
            self.assertTrue(snapshot["artifact_revision"])

    def test_invalid_manual_readiness_score_is_removed(self) -> None:
        report = (ROOT / "docs" / "governance-consolidation-report.md").read_text(encoding="utf-8")
        self.assertNotIn("36/100", report)


if __name__ == "__main__":
    unittest.main()
