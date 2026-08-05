import unittest
from datetime import datetime

from packages.domain import DealingRange, MarketObservation, RangeLocation


class DealingRangeTests(unittest.TestCase):
    def test_classifies_discount_equilibrium_and_premium(self) -> None:
        self.assertEqual(DealingRange(100, 200, 140).location(0.02), RangeLocation.DISCOUNT)
        self.assertEqual(DealingRange(100, 200, 150).location(0.02), RangeLocation.EQUILIBRIUM)
        self.assertEqual(DealingRange(100, 200, 160).location(0.02), RangeLocation.PREMIUM)

    def test_midpoint_uses_range_span(self) -> None:
        self.assertEqual(DealingRange(100, 300, 150).midpoint, 200)

    def test_rejects_invalid_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "high must be greater"):
            DealingRange(200, 100, 150)

    def test_rejects_price_outside_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "inside"):
            DealingRange(100, 200, 250)


class ObservationTests(unittest.TestCase):
    def test_requires_timezone_aware_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            MarketObservation("XAUUSD", "H1", datetime(2026, 1, 1), None, None, (), "test")

    def test_requires_identity_and_provenance(self) -> None:
        with self.assertRaisesRegex(ValueError, "source are required"):
            MarketObservation(
                "XAUUSD",
                "H1",
                datetime(2026, 1, 1).astimezone(),
                None,
                None,
                (),
                "",
            )


if __name__ == "__main__":
    unittest.main()
