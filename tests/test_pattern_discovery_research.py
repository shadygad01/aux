from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from backtest.mtf_models import Direction
from backtest.pattern_discovery_research import (
    LabeledOpportunity,
    Operator,
    discover_rules,
    generate_rules,
)


class PatternDiscoveryResearchTests(unittest.TestCase):
    def test_rules_are_interpretable_stable_and_direction_specific(self) -> None:
        start = datetime(2021, 1, 1, tzinfo=UTC)
        opportunities = [
            LabeledOpportunity(
                timestamp=start + timedelta(days=index * 10),
                exit_time=start + timedelta(days=index * 10, hours=1),
                direction=Direction.BUY,
                exit_plan_id="fixed_2R",
                features={"h1_sweep": True},
                net_r=1.0,
            )
            for index in range(72)
        ]
        rules = generate_rules(
            (Direction.BUY,),
            ("fixed_2R",),
            {"h1_sweep": ((Operator.EQ, True),)},
            maximum_conditions=1,
        )
        boundaries = (
            start,
            start + timedelta(days=240),
            start + timedelta(days=480),
            start + timedelta(days=720),
        )
        results = discover_rules(
            opportunities, rules, boundaries, minimum_fold_trades=20, fdr_alpha=0.05
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].accepted_by_fdr)
        self.assertEqual(results[0].rule.direction, Direction.BUY)


if __name__ == "__main__":
    unittest.main()
