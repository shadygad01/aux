import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYERS = {
    "packages/domain": (),
    "packages/application": ("packages.domain",),
    "packages/infrastructure": ("packages.domain", "packages.application"),
}


class ArchitectureTests(unittest.TestCase):
    def test_required_governance_records_exist(self) -> None:
        required = (
            "docs/roadmap.md",
            "docs/concept-ownership.md",
            "docs/lineage-contract.md",
            "docs/technical-debt-register.md",
            "docs/institutional-health-dashboard.md",
            "docs/architecture-entropy-report.md",
            "docs/governance-consolidation-report.md",
            "docs/capability-readiness-matrix.md",
            "docs/capability-dependency-graph.md",
            "docs/capability-maturity-report.md",
            "docs/capability-promotion-rules.md",
            "docs/capability-blocker-register.md",
            "docs/institutional-readiness-dashboard.md",
            "docs/project-readiness-formula.md",
            "docs/readiness-history.json",
            "docs/institutional-readiness-restructuring-report.md",
            "docs/adr/0001-capability-ownership.md",
            "docs/adr/0002-market-thesis-is-the-only-decision.md",
            "docs/adr/0003-canonical-lineage.md",
            "docs/adr/0004-institutional-quality-gate.md",
            "docs/adr/0005-compatibility-adapters.md",
            "docs/adr/0006-capability-derived-readiness.md",
        )
        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_layer_dependencies_point_inward(self) -> None:
        failures: list[str] = []
        for folder, allowed_internal in LAYERS.items():
            for path in (ROOT / folder).glob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.ImportFrom)
                        and node.module
                        and node.module.startswith("packages.")
                        and not node.module.startswith(allowed_internal)
                    ):
                        failures.append(f"{path.relative_to(ROOT)} imports {node.module}")
        self.assertEqual(failures, [])

    def test_production_code_does_not_use_any_or_cast(self) -> None:
        failures: list[str] = []
        for root in (ROOT / "apps", ROOT / "capabilities", ROOT / "packages"):
            for path in root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id in {"Any", "cast"}:
                        failures.append(f"{path.relative_to(ROOT)}:{node.lineno} uses {node.id}")
        self.assertEqual(failures, [])

    def test_capabilities_do_not_depend_on_ui_or_compatibility_adapters(self) -> None:
        forbidden_prefixes = ("apps", "packages.application")
        failures: list[str] = []
        for path in (ROOT / "capabilities").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith(forbidden_prefixes)
                ):
                    failures.append(f"{path.relative_to(ROOT)} imports {node.module}")
                if isinstance(node, ast.ClassDef) and node.name.endswith("Engine"):
                    failures.append(f"{path.relative_to(ROOT)} declares adapter-style {node.name}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
