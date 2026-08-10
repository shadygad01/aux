from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from backtest.mtf_research_cli import build_parser, main


class MtfResearchCliTests(unittest.TestCase):
    def test_defaults_keep_holdout_locked_to_last_two_years(self) -> None:
        args = build_parser().parse_args(["discover"])

        self.assertEqual(args.start, datetime(2021, 8, 8, tzinfo=UTC))
        self.assertEqual(args.holdout_start, datetime(2024, 8, 8, tzinfo=UTC))
        self.assertEqual(args.end, datetime(2026, 8, 8, tzinfo=UTC))
        self.assertEqual(args.embargo_hours, 120)

    def test_build_fails_closed_without_tick_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = main(
                [
                    "build",
                    "--raw-root",
                    str(root / "raw"),
                    "--derived-root",
                    str(root / "derived"),
                    "--report-root",
                    str(root / "reports"),
                ]
            )

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
