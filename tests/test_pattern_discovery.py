import unittest
from datetime import UTC, datetime

from packages.application import PatternDiscovery
from packages.domain import (
    DiscoveredPattern,
    PatternSource,
    PatternStatus,
    PatternValidation,
)
from packages.infrastructure import InMemoryPatternArchive

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def candidate(sample_size: int = 40) -> DiscoveredPattern:
    return DiscoveredPattern(
        "PATTERN-000001",
        1,
        "London discount sweeps under a reviewed macro regime.",
        ("decision:1", "evidence:2"),
        (PatternSource.DECISION_MEMORY, PatternSource.HISTORICAL_MARKET_DATA),
        sample_size,
        0.65,
        0.35,
        ("LONDON",),
        ("REAL_YIELDS_FALLING",),
        0.72,
        PatternStatus.EXPERIMENTAL,
        PatternValidation(),
        NOW,
        "Initial discovery",
    )


class PatternDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.archive = InMemoryPatternArchive()
        self.discovery = PatternDiscovery(self.archive)

    def test_one_event_and_direct_production_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple observations"):
            candidate(1)
        pattern = self.discovery.discover(candidate())
        self.assertFalse(pattern.production_eligible)
        with self.assertRaisesRegex(ValueError, "invalid pattern transition"):
            self.discovery.promote(
                pattern.pattern_id,
                PatternStatus.INSTITUTIONAL_PATTERN,
                PatternValidation(True, 3, True, True, True, ("study:1",)),
                NOW,
                "Attempted shortcut",
            )

    def test_full_validation_chain_is_append_only_and_production_gated(self) -> None:
        initial = self.discovery.discover(candidate())
        significant = PatternValidation(True, 2, False, False, False, ("stats:1",))
        observed = self.discovery.promote(
            initial.pattern_id, PatternStatus.OBSERVED, significant, NOW, "Repeated observation"
        )
        self.assertFalse(observed.production_eligible)
        with self.assertRaisesRegex(ValueError, "backtesting"):
            self.discovery.promote(
                initial.pattern_id, PatternStatus.VALIDATED, significant, NOW, "No backtest"
            )
        backtested = PatternValidation(True, 3, True, False, True, ("backtest:1",))
        validated = self.discovery.promote(
            initial.pattern_id, PatternStatus.VALIDATED, backtested, NOW, "Backtest passed"
        )
        self.assertFalse(validated.production_eligible)
        with self.assertRaisesRegex(ValueError, "forward testing"):
            self.discovery.promote(
                initial.pattern_id,
                PatternStatus.INSTITUTIONAL_PATTERN,
                backtested,
                NOW,
                "No forward test",
            )
        complete = PatternValidation(True, 4, True, True, True, ("forward:1", "docs:1"))
        institutional = self.discovery.promote(
            initial.pattern_id,
            PatternStatus.INSTITUTIONAL_PATTERN,
            complete,
            NOW,
            "All gates passed",
        )
        self.assertTrue(institutional.production_eligible)
        self.assertEqual(
            [item.revision for item in self.archive.history(initial.pattern_id)], [1, 2, 3, 4]
        )

    def test_validation_claims_require_references(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence references"):
            PatternValidation(statistically_significant=True, repeatability_runs=2)


if __name__ == "__main__":
    unittest.main()
