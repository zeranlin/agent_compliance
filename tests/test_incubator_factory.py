from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator import bootstrap_agent_factory, list_blueprints


class IncubatorFactoryTests(unittest.TestCase):
    def test_list_blueprints_returns_registered_blueprints(self) -> None:
        agent_keys = {blueprint.agent_key for blueprint in list_blueprints()}
        self.assertIn("compliance_review", agent_keys)
        self.assertIn("budget_demand", agent_keys)

    def test_bootstrap_agent_factory_generates_scaffold_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = bootstrap_agent_factory(Path(temp_dir), "budget_demand")

        self.assertEqual(result.blueprint.agent_key, "budget_demand")
        self.assertGreater(result.report["summary"]["completed_stages"], 0)
        self.assertIn("蒸馏报告", result.report_markdown)
        self.assertTrue(result.scaffold_plan.target_root.name.endswith("budget_demand"))


if __name__ == "__main__":
    unittest.main()
