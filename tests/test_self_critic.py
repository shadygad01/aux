import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from test_decision_memory import NOW, snapshot

from packages.application import DecisionMemory, SelfCritic
from packages.domain import CritiqueAssessment, CritiqueStage, DecisionOutcome
from packages.infrastructure import InMemoryCritiqueArchive, SqliteDecisionMemory


def assessment() -> CritiqueAssessment:
    return CritiqueAssessment(
        "No ignored evidence was found in the reviewed evidence set.",
        "Macro evidence may have received excessive weight.",
        "Contradicting liquidity evidence may have received insufficient weight.",
        "Uncertainty may be understated because sources share dependencies.",
        "Conflicting evidence existed in the liquidity graph.",
        "A contradiction-first path would have produced WAIT.",
        ("evidence:macro", "evidence:liquidity"),
    )


class SelfCriticTests(unittest.TestCase):
    def test_failed_decision_always_creates_research_task(self) -> None:
        with TemporaryDirectory() as directory:
            store = SqliteDecisionMemory(Path(directory) / "decisions.db")
            memory = DecisionMemory(store, store)
            original = memory.create(snapshot(), NOW, "Initial")
            failed = memory.evolve(
                original.decision_id,
                original.snapshot,
                NOW,
                "Outcome reviewed",
                DecisionOutcome.LOSING,
            )
            archive = InMemoryCritiqueArchive()
            critique, tasks = SelfCritic(archive, "critic-v1").challenge(
                failed, CritiqueStage.OUTCOME_REVIEW, assessment(), NOW
            )
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].critique_id, critique.critique_id)
            self.assertEqual(archive.tasks, list(tasks))

    def test_success_is_still_challenged_without_becoming_proof(self) -> None:
        with TemporaryDirectory() as directory:
            store = SqliteDecisionMemory(Path(directory) / "decisions.db")
            memory = DecisionMemory(store, store)
            original = memory.create(snapshot(), NOW, "Initial")
            winning = memory.evolve(
                original.decision_id,
                original.snapshot,
                NOW,
                "Outcome reviewed",
                DecisionOutcome.WINNING,
            )
            archive = InMemoryCritiqueArchive()
            critique, tasks = SelfCritic(archive, "critic-v1").challenge(
                winning, CritiqueStage.OUTCOME_REVIEW, assessment(), NOW
            )
            self.assertEqual(critique.outcome, DecisionOutcome.WINNING)
            self.assertEqual(tasks, ())
            self.assertEqual(len(archive.critiques), 1)

    def test_all_critic_questions_require_answers_and_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "every self-critic question"):
            CritiqueAssessment("", "answer", "answer", "answer", "answer", "answer", ())


if __name__ == "__main__":
    unittest.main()
