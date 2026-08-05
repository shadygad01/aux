import unittest
from datetime import UTC, datetime

from packages.application import TrustAssurance
from packages.domain import DecisionExplanation, ExplanationTrace, Recommendation

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
CANONICAL = '{"decision_id":"D1","evidence":["E1"],"policy":"P1"}'


def explanation() -> DecisionExplanation:
    trace = ExplanationTrace("reasoning:1", "knowledge:1", "evidence:1", "Price fact", "source:1")
    return DecisionExplanation(
        Recommendation.BUY_SETUPS_ONLY,
        ("Evidence favors BUY attention.",),
        ("Evidence is fresh.",),
        ("SELL lacks support.",),
        ("Mandatory evidence is complete.",),
        ("evidence:1",),
        ("A contradiction remains measurable.",),
        ("No mandatory information is missing.",),
        ("Evidence expiry invalidates the result.",),
        (trace,),
    )


class TrustAssuranceTests(unittest.TestCase):
    def test_manifest_exposes_required_fields_and_replays_input(self) -> None:
        trust = TrustAssurance.issue(
            explanation(), 82, 18, "policy:1", CANONICAL, "calculation:1", "audit:1", NOW
        )
        self.assertEqual(trust.facts, ("Price fact",))
        self.assertEqual(trust.confidence, 82)
        self.assertEqual(trust.uncertainty, 18)
        self.assertTrue(TrustAssurance.verifies_input(trust, CANONICAL))

    def test_changed_input_fails_replay_verification(self) -> None:
        trust = TrustAssurance.issue(
            explanation(), 82, 18, "policy:1", CANONICAL, "calculation:1", "audit:1", NOW
        )
        self.assertFalse(TrustAssurance.verifies_input(trust, CANONICAL + "changed"))

    def test_hidden_or_missing_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical replay input"):
            TrustAssurance.issue(
                explanation(), 82, 18, "policy:1", "", "calculation:1", "audit:1", NOW
            )


if __name__ == "__main__":
    unittest.main()
