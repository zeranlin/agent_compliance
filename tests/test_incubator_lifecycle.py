from __future__ import annotations

import unittest

from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    IncubationStage,
    SampleSet,
    ValidationComparison,
    create_incubation_run,
)


class IncubatorLifecycleTests(unittest.TestCase):
    def test_create_incubation_run_builds_all_default_stages(self) -> None:
        run = create_incubation_run("budget_demand", "预算智能体第一轮孵化")
        self.assertEqual(run.agent_key, "budget_demand")
        self.assertEqual(run.stages[0].stage, IncubationStage.REQUIREMENT_DEFINITION)
        self.assertEqual(run.stages[-1].stage, IncubationStage.PRODUCTIZATION)

    def test_stage_record_can_accumulate_samples_comparisons_and_recommendations(self) -> None:
        run = create_incubation_run("compliance_review", "合规智能体复盘")
        run.set_stage_status(IncubationStage.SAMPLE_PREPARATION, "completed", "样例已归档")
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
                target_agent_result="目标智能体漏掉评分结构",
                gap_points=("评分结构失衡未上浮",),
            ),
        )
        run.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="case-001:score-gap",
                title="增强评分语义",
                target_layer="scoring_semantic_consistency_engine",
                action="补评分结构失衡上浮逻辑",
                rationale="人工和强智能体都能抓到，目标智能体漏判。",
                priority="P0",
            ),
        )

        sample_stage = run.get_stage(IncubationStage.SAMPLE_PREPARATION)
        self.assertEqual(sample_stage.status, "completed")
        self.assertEqual(sample_stage.notes, "样例已归档")
        self.assertEqual(sample_stage.sample_sets[0].name, "第一批样例")

        validation_stage = run.get_stage(IncubationStage.PARITY_VALIDATION)
        self.assertEqual(validation_stage.comparisons[0].sample_id, "case-001")

        distill_stage = run.get_stage(IncubationStage.DISTILLATION_ITERATION)
        self.assertEqual(distill_stage.recommendations[0].priority, "P0")

    def test_run_can_update_recommendation_status(self) -> None:
        run = create_incubation_run("budget_demand", "预算智能体复盘")
        run.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="case-002:budget-gap",
                title="增强预算边界",
                target_layer="review_pipeline",
                action="补预算约束边界",
                rationale="当前预算边界仍未固化。",
            ),
        )

        run.update_recommendation_status(
            IncubationStage.DISTILLATION_ITERATION,
            "case-002:budget-gap",
            "implemented",
            "已完成第一版实现",
        )

        recommendation = run.get_stage(IncubationStage.DISTILLATION_ITERATION).recommendations[0]
        self.assertEqual(recommendation.status, "implemented")
        self.assertEqual(recommendation.resolution_notes, "已完成第一版实现")


if __name__ == "__main__":
    unittest.main()
