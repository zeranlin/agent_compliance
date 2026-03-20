from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator import (
    IncubationStage,
    ValidationComparison,
    bootstrap_agent_factory,
    build_sample_manifest,
    list_blueprints,
    resume_agent_factory,
)


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

    def test_bootstrap_agent_factory_can_ingest_samples_and_comparisons(self) -> None:
        manifest = build_sample_manifest(
            "第一批样例",
            positive_paths=("samples/positive/a.docx",),
            negative_paths=("samples/negative/b.docx",),
        )
        comparisons = (
            ValidationComparison(
                sample_id="case-001",
                human_baseline="人工抓到评分问题",
                strong_agent_result="强智能体抓到评分问题",
                target_agent_result="目标智能体漏判",
                gap_points=("评分结构失衡未上浮",),
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = bootstrap_agent_factory(
                Path(temp_dir),
                "compliance_review",
                sample_manifest=manifest,
                comparisons=comparisons,
            )

        sample_stage = result.run.get_stage(result.run.stages[1].stage)
        validation_stage = result.run.get_stage(result.run.stages[4].stage)
        distill_stage = result.run.get_stage(result.run.stages[5].stage)

        self.assertEqual(sample_stage.status, "completed")
        self.assertEqual(validation_stage.status, "completed")
        self.assertEqual(distill_stage.status, "in_progress")
        self.assertEqual(len(distill_stage.recommendations), 1)

    def test_resume_agent_factory_appends_follow_up_inputs(self) -> None:
        initial = bootstrap_agent_factory(Path(tempfile.gettempdir()), "budget_demand")
        manifest = build_sample_manifest(
            "补充样例",
            negative_paths=("samples/negative/z.docx",),
        )
        comparisons = (
            ValidationComparison(
                sample_id="case-002",
                human_baseline="人工抓到边界问题",
                strong_agent_result="强智能体抓到边界问题",
                target_agent_result="目标智能体误报",
                gap_points=("边界问题误报",),
            ),
        )

        resumed = resume_agent_factory(
            initial.run,
            sample_manifest=manifest,
            comparisons=comparisons,
        )

        self.assertIsNone(resumed.scaffold_plan)
        self.assertEqual(
            resumed.run.get_stage(IncubationStage.SAMPLE_PREPARATION).sample_sets[-1].name,
            "补充样例",
        )
        self.assertEqual(
            resumed.run.get_stage(IncubationStage.PARITY_VALIDATION).comparisons[-1].sample_id,
            "case-002",
        )


if __name__ == "__main__":
    unittest.main()
