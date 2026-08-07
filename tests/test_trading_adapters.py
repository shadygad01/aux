import unittest

from packages.domain import AttentionBias, TradingHorizon
from packages.infrastructure import trading_observation_from_json
from packages.infrastructure.errors import ContractValidationError
from packages.infrastructure.trading_adapters import trading_observation_to_json


def valid_payload() -> dict[str, object]:
    return {
        "contract_version": "1.0.0",
        "opportunity_id": "opp-001",
        "symbol": "XAUUSD",
        "execution_horizon": "SCALPING",
        "observed_at": "2026-08-05T11:30:00Z",
        "source": "contract-test",
        "macro": {
            "bias": "BUY_ONLY",
            "reasoning": "Dollar weakness supports gold.",
            "supporting_factors": ["dollar weakness"],
            "contradicting_factors": [],
            "confidence": 0.8,
        },
        "horizon_biases": [
            {"horizon": "LONG_TERM", "bias": "BUY_ONLY", "reasoning": "H4 bullish."},
            {"horizon": "MEDIUM_TERM", "bias": "BUY_ONLY", "reasoning": "H1 bullish."},
            {"horizon": "SCALPING", "bias": "BUY_ONLY", "reasoning": "M15 bullish."},
        ],
        "dealing_range": {"low": 4200.0, "high": 4300.0, "current_price": 4220.0},
        "nearby_liquidity_levels": ["PDL"],
        "momentum": {
            "macd_value": -3.5,
            "histogram": -1.2,
            "slope": None,
            "crossover_confirmed": False,
        },
        "smc": {
            "liquidity_event": {
                "side": "SELL_SIDE",
                "swept": True,
                "displacement_confirmed": True,
            },
            "reversal_candle_confirmed": True,
            "change_of_character": True,
            "order_block": True,
            "fair_value_gap": True,
        },
        "news": [],
    }


class TradingObservationFromJsonTests(unittest.TestCase):
    def test_parses_a_full_valid_payload(self) -> None:
        observation = trading_observation_from_json(valid_payload())
        self.assertEqual(observation.symbol, "XAUUSD")
        self.assertEqual(observation.execution_horizon, TradingHorizon.SCALPING)
        self.assertEqual(len(observation.horizon_biases), 3)
        assert observation.macro is not None
        self.assertEqual(observation.macro.bias, AttentionBias.BUY_ONLY)
        assert observation.dealing_range is not None
        self.assertEqual(observation.dealing_range.low, 4200.0)
        assert observation.momentum is not None
        self.assertEqual(observation.momentum.macd_value, -3.5)
        assert observation.smc is not None
        self.assertTrue(observation.smc.reversal_candle_confirmed)

    def test_parses_a_minimal_payload_with_no_optional_evidence(self) -> None:
        payload = valid_payload()
        for key in ("macro", "dealing_range", "momentum", "smc"):
            payload[key] = None
        payload["horizon_biases"] = []
        payload["nearby_liquidity_levels"] = []
        observation = trading_observation_from_json(payload)
        self.assertIsNone(observation.macro)
        self.assertIsNone(observation.dealing_range)
        self.assertIsNone(observation.momentum)
        self.assertIsNone(observation.smc)
        self.assertEqual(observation.horizon_biases, ())

    def test_rejects_unknown_contract_version(self) -> None:
        payload = valid_payload()
        payload["contract_version"] = "2.0.0"
        with self.assertRaisesRegex(
            ContractValidationError, "unsupported trading observation contract"
        ):
            trading_observation_from_json(payload)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ContractValidationError, r"path=\$"):
            trading_observation_from_json([])

    def test_rejects_missing_required_field(self) -> None:
        payload = valid_payload()
        del payload["opportunity_id"]
        with self.assertRaisesRegex(ContractValidationError, r"\$\.opportunity_id"):
            trading_observation_from_json(payload)

    def test_rejects_invalid_execution_horizon_enum(self) -> None:
        payload = valid_payload()
        payload["execution_horizon"] = "WEEKLY"
        with self.assertRaisesRegex(ContractValidationError, "invalid trading observation"):
            trading_observation_from_json(payload)

    def test_rejects_invalid_smc_liquidity_side(self) -> None:
        payload = valid_payload()
        smc = payload["smc"]
        assert isinstance(smc, dict)
        liquidity_event = smc["liquidity_event"]
        assert isinstance(liquidity_event, dict)
        liquidity_event["side"] = "MIDDLE_SIDE"
        with self.assertRaisesRegex(ContractValidationError, "invalid smc assessment"):
            trading_observation_from_json(payload)

    def test_failure_includes_exact_json_path(self) -> None:
        payload = valid_payload()
        payload["momentum"] = {"macd_value": "not-a-number"}
        with self.assertRaisesRegex(ContractValidationError, r"\$\.momentum\.macd_value"):
            trading_observation_from_json(payload)

    def test_rejects_non_array_news(self) -> None:
        payload = valid_payload()
        payload["news"] = {}
        with self.assertRaisesRegex(ContractValidationError, "expected array"):
            trading_observation_from_json(payload)

    def test_rejects_invalid_macro_bias_enum(self) -> None:
        payload = valid_payload()
        macro = payload["macro"]
        assert isinstance(macro, dict)
        macro["bias"] = "HOLD_FOREVER"
        with self.assertRaisesRegex(ContractValidationError, "invalid macro assessment"):
            trading_observation_from_json(payload)

    def test_rejects_non_array_horizon_biases(self) -> None:
        payload = valid_payload()
        payload["horizon_biases"] = {}
        with self.assertRaisesRegex(
            ContractValidationError, r"expected array; path=\$\.horizon_biases"
        ):
            trading_observation_from_json(payload)

    def test_rejects_invalid_horizon_bias_enum(self) -> None:
        payload = valid_payload()
        horizon_biases = payload["horizon_biases"]
        assert isinstance(horizon_biases, list)
        first = horizon_biases[0]
        assert isinstance(first, dict)
        first["horizon"] = "WEEKLY"
        with self.assertRaisesRegex(ContractValidationError, "invalid horizon bias"):
            trading_observation_from_json(payload)

    def test_rejects_invalid_dealing_range_number(self) -> None:
        payload = valid_payload()
        payload["dealing_range"] = {"low": True, "high": 4300.0, "current_price": 4220.0}
        with self.assertRaisesRegex(ContractValidationError, "invalid dealing range"):
            trading_observation_from_json(payload)

    def test_parses_smc_evidence_with_no_liquidity_event(self) -> None:
        payload = valid_payload()
        payload["smc"] = {"liquidity_event": None, "reversal_candle_confirmed": False}
        observation = trading_observation_from_json(payload)
        assert observation.smc is not None
        self.assertIsNone(observation.smc.liquidity_event)
        self.assertFalse(observation.smc.reversal_candle_confirmed)

    def test_parses_a_news_item(self) -> None:
        payload = valid_payload()
        payload["news"] = [
            {
                "effect": "SUPPORTS_BUY",
                "why": "Weak jobs report",
                "expected_impact": "Gold rallies",
                "expected_until": "2026-08-06T00:00:00Z",
                "confidence": 0.6,
            }
        ]
        observation = trading_observation_from_json(payload)
        self.assertEqual(len(observation.news), 1)
        self.assertEqual(observation.news[0].why, "Weak jobs report")

    def test_rejects_invalid_news_effect_enum(self) -> None:
        payload = valid_payload()
        payload["news"] = [
            {
                "effect": "CAUSES_CHAOS",
                "why": "n/a",
                "expected_impact": "n/a",
                "expected_until": "2026-08-06T00:00:00Z",
                "confidence": 0.5,
            }
        ]
        with self.assertRaisesRegex(ContractValidationError, "invalid news assessment"):
            trading_observation_from_json(payload)

    def test_rejects_non_array_supporting_factors(self) -> None:
        payload = valid_payload()
        macro = payload["macro"]
        assert isinstance(macro, dict)
        macro["supporting_factors"] = "not-a-list"
        with self.assertRaisesRegex(ContractValidationError, "invalid macro assessment"):
            trading_observation_from_json(payload)


class TradingObservationToJsonTests(unittest.TestCase):
    def test_round_trips_a_full_payload(self) -> None:
        observation = trading_observation_from_json(valid_payload())
        rendered = trading_observation_to_json(observation)
        self.assertEqual(rendered["symbol"], "XAUUSD")
        assert isinstance(rendered["smc"], dict)
        assert isinstance(rendered["smc"]["liquidity_event"], dict)
        self.assertEqual(rendered["smc"]["liquidity_event"]["side"], "SELL_SIDE")

    def test_renders_missing_optional_evidence_as_null(self) -> None:
        payload = valid_payload()
        for key in ("macro", "dealing_range", "momentum", "smc"):
            payload[key] = None
        payload["horizon_biases"] = []
        observation = trading_observation_from_json(payload)
        rendered = trading_observation_to_json(observation)
        self.assertIsNone(rendered["macro"])
        self.assertIsNone(rendered["dealing_range"])
        self.assertIsNone(rendered["momentum"])
        self.assertIsNone(rendered["smc"])

    def test_renders_smc_with_no_liquidity_event_as_null(self) -> None:
        payload = valid_payload()
        payload["smc"] = {"liquidity_event": None, "reversal_candle_confirmed": False}
        observation = trading_observation_from_json(payload)
        rendered = trading_observation_to_json(observation)
        assert isinstance(rendered["smc"], dict)
        self.assertIsNone(rendered["smc"]["liquidity_event"])


if __name__ == "__main__":
    unittest.main()
