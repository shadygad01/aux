import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.trading_cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class TradingCliIntegrationTests(unittest.TestCase):
    def test_example_produces_search_buy_setups_contract(self) -> None:
        with TemporaryDirectory() as tmp:
            output = StringIO()
            errors = StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(
                    [
                        str(ROOT / "examples" / "bullish_trading_evaluation.json"),
                        "--at",
                        "2026-08-05T12:00:00Z",
                        "--ledger",
                        str(Path(tmp) / "opportunities.jsonl"),
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["contract_version"], "2.0.0")
            self.assertEqual(payload["execution_status"], "SEARCH_BUY_SETUPS")
            self.assertEqual(payload["trade_quality"], 100)
            self.assertIn("trading_opportunity_evaluated", errors.getvalue())
            self.assertTrue((Path(tmp) / "opportunities.jsonl").exists())

    def test_rejects_a_malformed_observation_file(self) -> None:
        with TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text("{}", encoding="utf-8")
            errors = StringIO()
            with self.assertRaises(SystemExit), redirect_stderr(errors):
                main([str(bad_path), "--ledger", str(Path(tmp) / "opportunities.jsonl")])
            self.assertIn("error=", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
