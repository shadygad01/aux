"""Tests for the Capability Readiness / Institutional Health scope disclosure.

Capability Readiness measures the capabilities/* institutional governance
framework, not the live canonical trading pipeline -- but nothing on the
dashboard said so, so a stale, dormant-framework snapshot could be read as
a report on the live system's health. These tests guard the fix: the
snapshot's "scope" field must reach both published artifacts.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from publish.generators import health, readiness


class ReadinessScopeTests(unittest.TestCase):
    def test_capability_readiness_publishes_the_scope_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "capability_readiness.json"
            readiness.generate(out_file)
            artifact = json.loads(out_file.read_text(encoding="utf-8"))
            scope = artifact["payload"]["scope"]
            self.assertTrue(scope)
            self.assertIn("capabilities/*", scope)
            self.assertIn("DecisionEngine", scope)

    def test_institutional_health_carries_the_same_scope_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            readiness.generate(artifacts_dir / "capability_readiness.json")

            debt_artifact = {
                "payload": {
                    "items": [],
                    "p0_blocking_count": 0,
                    "p1_scale_count": 0,
                    "total_items": 0,
                }
            }
            (artifacts_dir / "technical_debt.json").write_text(
                json.dumps(debt_artifact), encoding="utf-8"
            )

            health_path = artifacts_dir / "institutional_health.json"
            health.generate(health_path, artifacts_dir)
            health_artifact = json.loads(health_path.read_text(encoding="utf-8"))

            readiness_artifact = json.loads(
                (artifacts_dir / "capability_readiness.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                health_artifact["payload"]["scope"], readiness_artifact["payload"]["scope"]
            )
            self.assertTrue(health_artifact["payload"]["scope"])


if __name__ == "__main__":
    unittest.main()
