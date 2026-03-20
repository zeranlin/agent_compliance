from __future__ import annotations

import unittest

from agent_compliance.incubator.evals.distillation_reporter import (
    build_distillation_report,
    render_distillation_report_markdown,
)
from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    IncubationStage,
    SampleSet,
    ValidationComparison,
    create_incubation_run,
)


class DistillationReporterTests(unittest.TestCase):
    def test_build_distillation_report_summarizes_run(self) -> None:
        run = create_incubation_run("compliance_review", "合规智能体第一轮蒸馏")
        run.set_stage_status(IncubationStage.SAMPLE_PREPARATION, "completed", "样例已整理")
        run.set_stage_status(IncubationStage.PARITY_VALIDATION, "completed")
        run.add_sample_set(
            IncubationStage.SAMPLE_PREPARATION,
            SampleSet(
                name="第一批样例",
                positive_examples=("positive-1",),
                negative_examples=("negative-1",),
            ),
        )
        run.add_comparison(
            IncubationStage.PARITY_VALIDATION,
            ValidationComparison(
                sample_id="case-001",
                human_baseline="人工抓到评分结构失衡",
                strong_agent_result="强智能体抓到评分主问题",
                target_agent_result="目标智能体漏判",
                gap_points=("评分主问题未上浮",),
                summary="目标智能体仍弱于人工与强智能体。",
            ),
        )
        run.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="case-001:score-gap",
                title="增强评分引擎",
                target_layer="scoring_semantic_consistency_engine",
                action="补评分结构失衡上浮逻辑",
                rationale="当前评分主问题漏判。",
                priority="P0",
                status="accepted",
                regression_result="评分样例回归通过",
                capability_change="已可稳定上浮评分结构失衡主问题",
            ),
        )

        report = build_distillation_report(run)
        self.assertEqual(report["agent_key"], "compliance_review")
        self.assertEqual(report["summary"]["sample_set_count"], 1)
        self.assertEqual(report["summary"]["comparison_count"], 1)
        self.assertEqual(report["summary"]["recommendation_count"], 1)
        self.assertEqual(report["summary"]["validated_change_count"], 1)
        self.assertGreaterEqual(report["summary"]["event_count"], 4)
        self.assertEqual(report["priority_summary"]["P0"], 1)
        self.assertEqual(report["recommendation_status_summary"]["accepted"], 1)
        self.assertEqual(
            report["target_layer_summary"]["scoring_semantic_consistency_engine"],
            1,
        )

    def test_render_markdown_includes_stage_and_summary(self) -> None:
        run = create_incubation_run("budget_demand", "预算智能体蒸馏")
        run.set_stage_status(IncubationStage.REQUIREMENT_DEFINITION, "completed")
        report = build_distillation_report(run)
        markdown = render_distillation_report_markdown(report)

        self.assertIn("# 预算智能体蒸馏 蒸馏报告", markdown)
        self.assertIn("## 阶段明细", markdown)
        self.assertIn("### requirement_definition", markdown)
        self.assertIn("阶段名称：业务需求定义", markdown)
        self.assertIn("执行痕迹", markdown)
        self.assertIn("尚未提供人工基准、强通用智能体结果和目标智能体结果的对照。", markdown)


if __name__ == "__main__":
    unittest.main()
