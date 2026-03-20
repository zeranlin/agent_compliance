from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.blueprints import (
    BUDGET_AGENT_BLUEPRINT,
    REVIEW_AGENT_BLUEPRINT,
)
from agent_compliance.incubator.scaffold_generator import (
    build_scaffold_plan,
    generate_agent_scaffold,
)


class ScaffoldGeneratorTests(unittest.TestCase):
    def test_build_scaffold_plan_uses_blueprint_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            plan = build_scaffold_plan(base_dir, REVIEW_AGENT_BLUEPRINT)
            self.assertEqual(plan.target_root, base_dir / "compliance_review")
            self.assertIn(base_dir / "compliance_review" / "rules", plan.directories)
            self.assertIn(
                base_dir / "compliance_review" / "pipeline.py",
                plan.files,
            )

    def test_generate_agent_scaffold_creates_minimal_budget_agent_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            plan = generate_agent_scaffold(base_dir, BUDGET_AGENT_BLUEPRINT)
            self.assertTrue((plan.target_root / "schemas.py").exists())
            self.assertTrue((plan.target_root / "pipeline.py").exists())
            self.assertTrue((plan.target_root / "service.py").exists())
            self.assertTrue((plan.target_root / "rules" / "__init__.py").exists())
            self.assertTrue((plan.target_root / "analyzers" / "__init__.py").exists())
            content = (plan.target_root / "pipeline.py").read_text(encoding="utf-8")
            self.assertIn("budget_demand", content)


if __name__ == "__main__":
    unittest.main()
