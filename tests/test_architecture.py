import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_publisher_has_one_product_artifact(self) -> None:
        source = (ROOT / "publish/generate_artifacts.py").read_text(encoding="utf-8")
        self.assertIn('("market_data.json", market_data.generate)', source)
        for retired in ("decision.generate", "market_thesis.generate", "readiness.generate"):
            self.assertNotIn(retired, source)

    def test_browser_has_no_decision_artifact_dependency(self) -> None:
        app = (ROOT / "docs/app.js").read_text(encoding="utf-8")
        self.assertIn("market_data.json", app)
        for name in ("decision.json", "policy.json", "multi_timeframe.json"):
            self.assertNotIn(name, app)

    def test_production_import_graph_has_no_application_layer(self) -> None:
        for folder in (ROOT / "publish", ROOT / "packages/infrastructure"):
            for path in folder.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                imports = [
                    node.module
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and node.module
                ]
                self.assertFalse(
                    any(module.startswith("packages.application") for module in imports),
                    f"production import leak in {path}",
                )
