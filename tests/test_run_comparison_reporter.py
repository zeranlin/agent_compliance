from __future__ import annotations

import unittest

from agent_compliance.incubator.evals import (
    build_run_comparison_report,
    render_run_comparison_markdown,
)
from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    IncubationStage,
    ValidationComparison,
    create_incubation_run,
)


class RunComparisonReporterTests(unittest.TestCase):
    def test_build_run_comparison_report_summarizes_multiple_runs(self) -> None:
        run1 = create_incubation_run("demand_research", "第一轮孵化")
        run1.set_stage_status(IncubationStage.PARITY_VALIDATION, "completed")
        run1.add_comparison(
            IncubationStage.PARITY_VALIDATION,
            ValidationComparison(
                sample_id="case-001",
                human_baseline="人工有需求结构",
                strong_agent_result="强智能体有需求结构",
                target_agent_result="目标智能体没有需求结构",
                gap_points=("需求章节结构尚未固化", "待人工补充项尚未标准化输出"),
            ),
        )
        run1.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="case-001:structure-gap",
                title="增强结构生成",
                target_layer="review_pipeline",
                action="补需求章节结构",
                rationale="结构仍缺失",
                priority="P1",
                regression_result="章节结构样例已回归",
                capability_change="已能输出需求章节骨架",
            ),
        )

        run2 = create_incubation_run("demand_research", "第二轮孵化")
        run2.set_stage_status(IncubationStage.PARITY_VALIDATION, "completed")
        run2.add_comparison(
            IncubationStage.PARITY_VALIDATION,
            ValidationComparison(
                sample_id="case-002",
                human_baseline="人工有需求结构和预算边界",
                strong_agent_result="强智能体有需求结构和预算边界",
                target_agent_result="目标智能体仅有需求结构",
                aligned_points=("需求章节结构尚未固化",),
                gap_points=("预算约束尚未转换成需求边界",),
            ),
        )
        run2.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="case-002:budget-gap",
                title="增强边界识别",
                target_layer="mixed_scope_boundary_engine",
                action="补预算边界约束",
                rationale="预算边界仍缺失",
                priority="P1",
            ),
        )

        report = build_run_comparison_report((run1, run2))

        self.assertEqual(report["agent_key"], "demand_research")
        self.assertEqual(report["run_count"], 2)
        self.assertEqual(report["trend"]["gap_delta"], -1)
        self.assertEqual(report["trend"]["validated_change_delta"], -1)
        self.assertTrue(report["trend"]["is_gap_converging"])

    def test_render_run_comparison_markdown_includes_summary(self) -> None:
        run = create_incubation_run("demand_research", "第一轮孵化")
        report = build_run_comparison_report((run,))
        markdown = render_run_comparison_markdown(report)

        self.assertIn("# demand_research 多轮孵化对比报告", markdown)
        self.assertIn("## 各轮摘要", markdown)
        self.assertIn("### 第一轮孵化", markdown)


if __name__ == "__main__":
    unittest.main()
