from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backtest.research_governance import (
    DirectionMetrics,
    ResearchSplit,
    benjamini_hochberg,
    calculate_metrics,
    evaluate_acceptance,
    freeze_configuration,
    holdout_rows,
)


class MtfResearchGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.split = ResearchSplit(
            datetime(2021, 8, 8, tzinfo=UTC),
            datetime(2024, 8, 8, tzinfo=UTC),
            datetime(2026, 8, 8, tzinfo=UTC),
            timedelta(days=5),
        )

    def test_holdout_is_inaccessible_before_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "missing.json"
            with self.assertRaisesRegex(PermissionError, "locked"):
                holdout_rows([], self.split, lambda item: item, frozen_configuration=path)

    def test_tampered_freeze_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "frozen.json"
            freeze_configuration(
                self.split,
                [{"pattern_id": "PAT-1"}],
                path,
                frozen_at=datetime(2024, 8, 7, tzinfo=UTC),
            )
            payload = json.loads(path.read_text())
            payload["selected_patterns"][0]["pattern_id"] = "PAT-TAMPERED"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(PermissionError, "hash mismatch"):
                holdout_rows([], self.split, lambda item: item, frozen_configuration=path)

    def test_benjamini_hochberg_controls_multiple_comparisons(self) -> None:
        accepted = benjamini_hochberg({"a": 0.001, "b": 0.02, "c": 0.9}, alpha=0.05)
        self.assertEqual(accepted, {"a", "b"})

    def test_under_sixty_trades_abstains(self) -> None:
        metrics = DirectionMetrics(
            59,
            1.0,
            0.5,
            2.0,
            59.0,
            2.0,
            2,
            {2025: 20.0},
            0.1,
            0.2,
        )
        result = evaluate_acceptance(
            metrics,
            stressed_net_r=10,
            neighboring_parameter_net_r=(5, 6),
            holdout_period_net_r=(5, 5),
        )
        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")

    def test_supported_requires_both_rolling_holdout_periods(self) -> None:
        metrics = DirectionMetrics(
            100,
            0.3,
            0.1,
            1.5,
            30.0,
            5.0,
            4,
            {2024: 5.0, 2025: 20.0, 2026: 5.0},
            0.1,
            0.2,
        )
        accepted = evaluate_acceptance(
            metrics,
            stressed_net_r=3.0,
            neighboring_parameter_net_r=(2.0, 1.0),
            holdout_period_net_r=(12.0, 18.0),
        )
        rejected = evaluate_acceptance(
            metrics,
            stressed_net_r=3.0,
            neighboring_parameter_net_r=(2.0, 1.0),
            holdout_period_net_r=(30.0, 0.0),
        )

        self.assertEqual(accepted.status, "SUPPORTED")
        self.assertIn("12-month", rejected.failures[0])

    def test_month_profit_concentration_is_calculated_separately(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        trades = [(start + timedelta(days=index), 1.0) for index in range(5)]
        trades.extend((start + timedelta(days=40 + index), 1.0) for index in range(5))

        metrics = calculate_metrics(trades)

        self.assertEqual(metrics.largest_profit_concentration, 0.1)
        self.assertEqual(metrics.largest_month_concentration, 0.5)


if __name__ == "__main__":
    unittest.main()
