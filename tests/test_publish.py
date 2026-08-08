"""Tests for the static publishing artifact generation pipeline."""

import json
import tempfile
import unittest
from pathlib import Path

import publish.generate_artifacts as generate_artifacts_module
from publish.generate_artifacts import run
from publish.generators import policy as policy_generator
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
            "execution_readiness.json",
            "opportunity_identity.json",
            "multi_timeframe.json",
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


class PublishFailureHandlingTests(unittest.TestCase):
    """Regression coverage for run()'s own failure-isolation and exit-code
    behavior -- the property .github/workflows/publish.yml depends on to
    never commit a partial or failed artifact set: the "Commit and push
    generated artifacts" step only runs if the "Generate all capability
    artifacts" step (i.e. run()) exits 0. This was previously verified only
    by reading the code; it had no regression test."""

    def test_a_failing_generator_fails_the_whole_run_without_corrupting_others(self) -> None:
        original_artifacts_dir = generate_artifacts_module.ARTIFACTS_DIR
        original_generators = list(generate_artifacts_module.GENERATORS)

        def failing_generator(output_path: Path) -> None:
            raise RuntimeError("simulated generator failure")

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_artifacts_module.ARTIFACTS_DIR = Path(tmpdir)
            generate_artifacts_module.GENERATORS = [
                ("policy.json", policy_generator.generate),
                ("broken.json", failing_generator),
            ]
            try:
                exit_code = generate_artifacts_module.run()
            finally:
                generate_artifacts_module.ARTIFACTS_DIR = original_artifacts_dir
                generate_artifacts_module.GENERATORS = original_generators

            # A failing generator must fail the whole run -- this is the exit
            # code publish.yml relies on to skip the commit step entirely.
            self.assertEqual(exit_code, 1)

            # One failure does not silently corrupt, skip, or fake an
            # unrelated artifact -- policy.json still generated correctly.
            policy_path = Path(tmpdir) / "policy.json"
            self.assertTrue(policy_path.exists())
            policy_content = json.loads(policy_path.read_text(encoding="utf-8"))
            self.assertIn("payload", policy_content)

            # The failing artifact must not exist, and manifest.json must not
            # claim it succeeded -- a reader of the manifest can trust that
            # every listed file is genuinely current, not a stale leftover
            # masquerading as a fresh, successful generation.
            self.assertFalse((Path(tmpdir) / "broken.json").exists())
            manifest = json.loads((Path(tmpdir) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("broken.json", manifest["artifacts"])
            self.assertIn("policy.json", manifest["artifacts"])
