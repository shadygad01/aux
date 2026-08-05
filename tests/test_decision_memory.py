import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import DecisionMemory
from packages.domain import (
    AttentionBias,
    DecisionGraph,
    DecisionOutcome,
    DecisionSearch,
    DecisionSearchKind,
    DecisionSnapshot,
    GraphNode,
    HorizonBias,
    MarketState,
    RangeLocation,
    Recommendation,
    TradingHorizon,
)
from packages.infrastructure import SqliteDecisionMemory

NOW = datetime(2026, 8, 5, 9, tzinfo=UTC)


def snapshot(state: Recommendation = Recommendation.WAIT, quality: int = 70) -> DecisionSnapshot:
    graph = DecisionGraph((GraphNode("n1", "evidence", "Macro", "audit-1"),), ())
    market = MarketState(
        "state-1",
        "XAUUSD",
        NOW,
        timedelta(minutes=15),
        3350,
        RangeLocation.DISCOUNT,
        "LONDON",
        "NORMAL",
        "Reviewed state",
        (),
        "feed",
    )
    return DecisionSnapshot(
        market,
        "Macro reviewed",
        (HorizonBias(TradingHorizon.MEDIUM_TERM, AttentionBias.BUY_ONLY, "bias"),),
        quality,
        state,
        graph,
        ("knowledge-1",),
        graph,
        DecisionGraph((), ()),
        80,
        20,
        ("macro",),
        (),
        ("SELL rejected",),
    )


class DecisionMemoryTests(unittest.TestCase):
    def test_ids_versions_changes_and_required_searches(self) -> None:
        with TemporaryDirectory() as directory:
            store = SqliteDecisionMemory(Path(directory) / "decisions.db")
            memory = DecisionMemory(store, store)
            first = memory.create(snapshot(), NOW, "Initial evaluation")
            buy = memory.evolve(
                first.decision_id,
                snapshot(Recommendation.BUY_SETUPS_ONLY, 92),
                NOW + timedelta(minutes=15),
                "Sweep confirmed",
            )
            memory.evolve(
                first.decision_id,
                buy.snapshot,
                NOW + timedelta(minutes=30),
                "Outcome reviewed",
                DecisionOutcome.LOSING,
            )
            rejected = memory.create(snapshot(), NOW + timedelta(hours=1), "Rejected setup")
            memory.evolve(
                rejected.decision_id,
                rejected.snapshot,
                NOW + timedelta(hours=2),
                "Counterfactual reviewed",
                DecisionOutcome.REJECTED_WOULD_WIN,
            )
            self.assertEqual(first.decision_id, "DECISION-20260805-000001")
            self.assertEqual(buy.version, 2)
            self.assertTrue(any(change.field == "execution_state" for change in buy.changes))
            self.assertEqual(
                memory.search(DecisionSearch(DecisionSearchKind.BUY_ABOVE_QUALITY, 90)).total, 2
            )
            self.assertEqual(
                memory.search(
                    DecisionSearch(DecisionSearchKind.FAILED_BUY_ABOVE_QUALITY, 85)
                ).total,
                1,
            )
            self.assertEqual(
                memory.search(DecisionSearch(DecisionSearchKind.WAIT_LATER_BECAME_BUY)).total, 1
            )
            self.assertEqual(
                memory.search(DecisionSearch(DecisionSearchKind.REJECTED_WOULD_HAVE_WON)).total, 1
            )

            reopened_store = SqliteDecisionMemory(Path(directory) / "decisions.db")
            reopened = DecisionMemory(reopened_store, reopened_store)
            restored = reopened_store.latest(first.decision_id)
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.snapshot.evidence_graph, first.snapshot.evidence_graph)
            self.assertEqual(
                reopened.search(DecisionSearch(DecisionSearchKind.WAIT_LATER_BECAME_BUY)).total, 1
            )
            evolved = reopened.evolve(
                first.decision_id,
                snapshot(Recommendation.SELL_SETUPS_ONLY, 60),
                NOW + timedelta(hours=3),
                "Evidence reversed after restart",
            )
            self.assertEqual(evolved.version, 4)

    def test_rejects_unknown_and_no_change_evolution(self) -> None:
        with TemporaryDirectory() as directory:
            store = SqliteDecisionMemory(Path(directory) / "decisions.db")
            memory = DecisionMemory(store, store)
            with self.assertRaises(ValueError):
                memory.evolve("missing", snapshot(), NOW, "reason")
            first = memory.create(snapshot(), NOW, "initial")
            with self.assertRaisesRegex(ValueError, "no changes"):
                memory.evolve(first.decision_id, first.snapshot, NOW, "same")


if __name__ == "__main__":
    unittest.main()
