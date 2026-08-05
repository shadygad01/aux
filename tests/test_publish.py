"""Tests for the static publishing artifact generation pipeline."""

import json
import tempfile
import unittest
from pathlib import Path

from publish.generate_artifacts import run
from publish.generators.envelope import build_envelope


class PublishTests(unittest.TestCase):
    def test_build_envelope_contains_all_required_metadata_fields(self) -> None:
        envelope = build_envelope(
            generator="publish.generators.test",
            schema_version="1.0.0",
            payload={"key": "value"},
        )
        self.assertEqual(envelope["artifact_version"], "1.0.0")
        self.assertIn("generated_at", envelope)
        self.assertIn("commit", envelope)
        self.assertEqual(envelope["generator"], "publish.generators.test")
        self.assertEqual(envelope["schema_version"], "1.0.0")
        self.assertEqual(envelope["payload"], {"key": "value"})

    def test_generate_artifacts_produces_all_expected_json_files(self) -> None:
        exit_code = run()
        self.assertEqual(exit_code, 0)

        artifacts_dir = Path("docs/artifacts")
        expected_files = (
            "decision.json",
            "policy.json",
            "capability_readiness.json",
            "technical_debt.json",
            "hypothesis_register.json",
            "institutional_health.json",
            "manifest.json",
        )
        for filename in expected_files:
            file_path = artifacts_dir / filename
            self.assertTrue(file_path.exists(), f"Missing expected artifact: {filename}")
            content = json.loads(file_path.read_text(encoding="utf-8"))
            if filename != "manifest.json":
                self.assertIn("artifact_version", content)
                self.assertIn("generator", content)
                self.assertIn("payload", content)
