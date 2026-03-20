from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    IncubationStage,
    create_incubation_run,
)
from agent_compliance.incubator.productize import (
    build_productization_package,
    render_productization_markdown,
    write_productization_package,
)


class ProductizeTests(unittest.TestCase):
    def test_build_productization_package_includes_release_templates(self) -> None:
        run = create_incubation_run("demand_research", "第一轮孵化")
        run.set_stage_status(IncubationStage.REQUIREMENT_DEFINITION, "completed")
        run.set_stage_status(IncubationStage.STRONG_AGENT_DESIGN, "completed")
        run.set_stage_status(IncubationStage.TARGET_AGENT_BOOTSTRAP, "completed")
        run.set_stage_status(IncubationStage.PARITY_VALIDATION, "completed")
        run.set_stage_status(IncubationStage.DISTILLATION_ITERATION, "completed")
        run.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="rec-001",
                title="增强结构生成",
                target_layer="pipeline",
                action="补章节生成",
                rationale="结构还不稳",
                status="validated",
                regression_result="结构样例回归通过",
                capability_change="已稳定输出章节骨架",
            ),
        )

        package = build_productization_package(run)

        self.assertEqual(package["readiness_level"], "pilot_ready")
        self.assertTrue(package["release_checklist"][0]["done"])
        self.assertEqual(len(package["ops_guidance"]), 4)
        self.assertEqual(len(package["delivery_template"]), 3)
        self.assertEqual(len(package["acceptance_template"]), 3)

    def test_write_productization_package_writes_json_and_markdown(self) -> None:
        run = create_incubation_run("budget_demand", "第一轮孵化")
        package = build_productization_package(run)
        markdown = render_productization_markdown(package)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_productization_package(
                Path(tmpdir),
                "budget_demand",
                "run-001",
                package,
                markdown,
            )
            self.assertTrue(paths.json_path.exists())
            self.assertTrue(paths.markdown_path.exists())
            self.assertIn("产品化固化模板", paths.markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
