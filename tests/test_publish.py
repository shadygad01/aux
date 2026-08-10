import json
import tempfile
import unittest
from pathlib import Path

import publish.generate_artifacts as publisher
from publish.generators.envelope import build_envelope


class PublishTests(unittest.TestCase):
    def test_dashboard_consumes_only_the_market_snapshot(self) -> None:
        html = Path("docs/index.html").read_text(encoding="utf-8")
        app = Path("docs/app.js").read_text(encoding="utf-8")
        self.assertIn("DIRECTIONAL <span>GUIDANCE</span>", html)
        self.assertIn("guidance-label", app)
        self.assertIn("fetchArtifact('market_data.json')", app)
        forbidden = ("decision.json", "market_thesis.json", "opportunity_identity.json")
        self.assertTrue(all(name not in app for name in forbidden))

    def test_envelope_is_auditable(self) -> None:
        envelope = build_envelope("test", "1.0.0", {"value": 1})
        self.assertEqual(envelope["generator"], "test")
        self.assertIn("generated_at", envelope)
        self.assertIn("commit", envelope)

    def test_generation_publishes_only_market_data_and_manifest(self) -> None:
        self.assertEqual(publisher.run(), 0)
        manifest = json.loads(Path("docs/artifacts/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["artifacts"], ["market_data.json"])

    def test_generator_failure_is_fail_closed(self) -> None:
        original_dir, original_generators = publisher.ARTIFACTS_DIR, publisher.GENERATORS

        def good(path: Path) -> None:
            path.write_text("{}", encoding="utf-8")

        def bad(path: Path) -> None:
            raise RuntimeError("failure")

        with tempfile.TemporaryDirectory() as directory:
            publisher.ARTIFACTS_DIR = Path(directory)
            publisher.GENERATORS = [("good.json", good), ("bad.json", bad)]
            try:
                self.assertEqual(publisher.run(), 1)
                manifest = json.loads((Path(directory) / "manifest.json").read_text())
                self.assertEqual(manifest["artifacts"], ["good.json"])
            finally:
                publisher.ARTIFACTS_DIR = original_dir
                publisher.GENERATORS = original_generators
