import unittest

from packages.infrastructure import observation_from_json
from packages.infrastructure.errors import ContractValidationError


def valid_payload() -> dict[str, object]:
    return {
        "contract_version": "1.0.0",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "observed_at": "2026-08-05T11:30:00Z",
        "source": "contract-test",
        "structure": {"bias": "BULLISH", "break_of_structure": True},
        "dealing_range": {"low": 3300, "high": 3400, "current_price": 3340},
        "liquidity": [{"side": "SELL_SIDE", "swept": True, "displacement_confirmed": True}],
    }


class MacdValueContractTests(unittest.TestCase):
    def test_defaults_to_none_when_absent(self) -> None:
        observation = observation_from_json(valid_payload())
        self.assertIsNone(observation.macd_value)

    def test_parses_a_provided_macd_value(self) -> None:
        payload = valid_payload()
        payload["macd_value"] = -2.5
        observation = observation_from_json(payload)
        self.assertEqual(observation.macd_value, -2.5)

    def test_rejects_non_numeric_macd_value(self) -> None:
        payload = valid_payload()
        payload["macd_value"] = "not-a-number"
        with self.assertRaisesRegex(ContractValidationError, "macd_value"):
            observation_from_json(payload)


class JsonContractTests(unittest.TestCase):
    def test_parses_versioned_observation(self) -> None:
        observation = observation_from_json(valid_payload())
        self.assertEqual(observation.symbol, "XAUUSD")
        self.assertEqual(len(observation.liquidity), 1)

    def test_rejects_unknown_contract_version(self) -> None:
        payload = valid_payload()
        payload["contract_version"] = "2.0.0"
        with self.assertRaisesRegex(ContractValidationError, "unsupported observation contract"):
            observation_from_json(payload)

    def test_failure_includes_exact_json_path(self) -> None:
        payload = valid_payload()
        payload["liquidity"] = [{"side": "SELL_SIDE", "swept": "yes"}]
        with self.assertRaisesRegex(ContractValidationError, r"\$\.liquidity\[0\]\.swept"):
            observation_from_json(payload)

    def test_rejects_boolean_as_number(self) -> None:
        payload = valid_payload()
        payload["dealing_range"] = {"low": True, "high": 3400, "current_price": 3340}
        with self.assertRaisesRegex(ContractValidationError, "expected number"):
            observation_from_json(payload)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ContractValidationError, r"path=\$"):
            observation_from_json([])

    def test_rejects_missing_required_field(self) -> None:
        payload = valid_payload()
        del payload["source"]
        with self.assertRaisesRegex(ContractValidationError, r"\$\.source"):
            observation_from_json(payload)

    def test_rejects_invalid_structure_enum(self) -> None:
        payload = valid_payload()
        payload["structure"] = {"bias": "SIDEWAYS", "break_of_structure": True}
        with self.assertRaisesRegex(ContractValidationError, "invalid market structure"):
            observation_from_json(payload)

    def test_rejects_non_array_liquidity(self) -> None:
        payload = valid_payload()
        payload["liquidity"] = {}
        with self.assertRaisesRegex(ContractValidationError, "expected array"):
            observation_from_json(payload)


if __name__ == "__main__":
    unittest.main()
