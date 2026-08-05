import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from apps.decision_cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class CliIntegrationTests(unittest.TestCase):
    def test_example_produces_backward_compatible_buy_contract(self) -> None:
        output = StringIO()
        errors = StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            result = main(
                [
                    str(ROOT / "examples" / "bullish_evaluation.json"),
                    "--at",
                    "2026-08-05T12:00:00Z",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["contract_version"], "1.0.0")
        self.assertEqual(payload["verdict"], "BUY")
        self.assertEqual(payload["score"], 1.0)
        self.assertIn("decision_evaluated", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
