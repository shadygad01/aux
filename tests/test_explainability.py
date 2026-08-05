import unittest

from packages.domain import DecisionExplanation, ExplanationTrace, Recommendation


def trace(evidence: str = "evidence:1") -> ExplanationTrace:
    return ExplanationTrace("reasoning:1", "knowledge:1", evidence, "Observed fact", "source:1")


def explanation(
    why_now: tuple[str, ...] = ("Fresh evidence remains inside its TTL.",),
    supporting_evidence: tuple[str, ...] = ("evidence:1",),
) -> DecisionExplanation:
    return DecisionExplanation(
        Recommendation.BUY_SETUPS_ONLY,
        ("Current evidence favors BUY attention.",),
        why_now,
        ("SELL lacks confirmed supporting evidence.",),
        ("All mandatory execution evidence is complete.",),
        supporting_evidence,
        ("No reviewed contradiction is currently active.",),
        ("No mandatory information is missing.",),
        ("Expiry or opposing evidence invalidates the decision.",),
        (trace(),),
    )


class ExplainabilityTests(unittest.TestCase):
    def test_complete_answers_and_lineage_are_accepted(self) -> None:
        value = explanation()
        self.assertEqual(value.traces[0].source, "source:1")

    def test_no_answer_may_be_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit answer"):
            explanation(why_now=())

    def test_supporting_evidence_must_reach_a_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "resolve"):
            explanation(supporting_evidence=("evidence:missing",))

    def test_trace_cannot_skip_a_tree_level(self) -> None:
        with self.assertRaisesRegex(ValueError, "reasoning-to-source"):
            trace("")


if __name__ == "__main__":
    unittest.main()
