from __future__ import annotations

import unittest

from packages.domain.guidance import build_directional_guidance


def guidance(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "data_status": "CURRENT",
        "synchronized": True,
        "structure": "BULLISH",
        "macd_line": 2.0,
        "signal_line": 1.0,
        "histogram": 1.0,
        "macro_balance": "TAILWIND",
    }
    values.update(overrides)
    return build_directional_guidance(**values)  # type: ignore[arg-type]


class DirectionalGuidanceTests(unittest.TestCase):
    def test_unanimous_buy_inputs_produce_lean_buy(self) -> None:
        result = guidance()
        self.assertEqual((result["label"], result["consistency"]), ("LEAN_BUY", "CONSISTENT"))

    def test_unanimous_sell_inputs_produce_lean_sell(self) -> None:
        result = guidance(
            structure="BEARISH",
            macd_line=-2.0,
            signal_line=-1.0,
            histogram=-1.0,
            macro_balance="HEADWIND",
        )
        self.assertEqual((result["label"], result["consistency"]), ("LEAN_SELL", "CONSISTENT"))

    def test_conflict_is_neutral(self) -> None:
        result = guidance(macro_balance="HEADWIND")
        self.assertEqual((result["label"], result["consistency"]), ("NEUTRAL", "CONFLICT"))

    def test_stale_or_missing_data_is_neutral(self) -> None:
        self.assertEqual(guidance(data_status="STALE")["consistency"], "INSUFFICIENT_DATA")
        self.assertEqual(guidance(macd_line=None)["label"], "NEUTRAL")

    def test_guidance_never_has_execution_authority(self) -> None:
        self.assertIs(guidance()["execution_authority"], False)
