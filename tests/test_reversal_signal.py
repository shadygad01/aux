from __future__ import annotations

import unittest

from packages.domain.reversal_signal import build_reversal_signal


def reversal(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "data_status": "CURRENT",
        "structure_bias": "BULLISH",
        "break_of_structure": True,
        "change_of_character": False,
        "range_location": "PREMIUM",
        "macd_line": 1.5,
    }
    values.update(overrides)
    return build_reversal_signal(**values)  # type: ignore[arg-type]


class ReversalSignalTests(unittest.TestCase):
    def test_bullish_bos_in_premium_with_positive_macd_watches_sell(self) -> None:
        result = reversal()
        self.assertEqual(result["label"], "WATCH_SELL")

    def test_bullish_choch_in_premium_with_positive_macd_watches_sell(self) -> None:
        result = reversal(break_of_structure=False, change_of_character=True)
        self.assertEqual(result["label"], "WATCH_SELL")

    def test_bearish_bos_in_discount_with_negative_macd_watches_buy(self) -> None:
        result = reversal(
            structure_bias="BEARISH",
            break_of_structure=True,
            change_of_character=False,
            range_location="DISCOUNT",
            macd_line=-1.5,
        )
        self.assertEqual(result["label"], "WATCH_BUY")

    def test_no_structural_break_is_none(self) -> None:
        result = reversal(break_of_structure=False, change_of_character=False)
        self.assertEqual(result["label"], "NONE")

    def test_wrong_zone_is_none(self) -> None:
        result = reversal(range_location="DISCOUNT")
        self.assertEqual(result["label"], "NONE")

    def test_macd_already_flipped_is_none(self) -> None:
        result = reversal(macd_line=-0.5)
        self.assertEqual(result["label"], "NONE")

    def test_missing_input_is_unavailable(self) -> None:
        self.assertEqual(reversal(macd_line=None)["label"], "UNAVAILABLE")
        self.assertEqual(reversal(structure_bias="NEUTRAL")["label"], "UNAVAILABLE")
        self.assertEqual(reversal(range_location=None)["label"], "UNAVAILABLE")

    def test_stale_or_unavailable_m15_snapshot_is_unavailable(self) -> None:
        self.assertEqual(reversal(data_status="STALE")["label"], "UNAVAILABLE")
        self.assertEqual(reversal(data_status="UNAVAILABLE")["label"], "UNAVAILABLE")

    def test_reversal_signal_never_has_execution_authority(self) -> None:
        self.assertIs(reversal()["execution_authority"], False)
        self.assertIs(reversal()["validated"], False)
