from __future__ import annotations

import unittest

from agent_compliance.incubator.distillation_engine import (
    build_distillation_recommendations,
    summarize_validation_gaps,
)
from agent_compliance.incubator.lifecycle import ValidationComparison


class DistillationEngineTests(unittest.TestCase):
    def test_build_distillation_recommendations_maps_gaps_to_target_layers(self) -> None:
        comparisons = (
            ValidationComparison(
                sample_id="case-001",
                human_baseline="人工抓到评分结构失衡",
                strong_agent_result="强智能体抓到评分主问题",
                target_agent_result="目标智能体漏判",
                gap_points=("评分结构失衡未上浮", "商务链条归并过宽"),
            ),
        )

        recommendations = build_distillation_recommendations(comparisons)

        self.assertEqual(len(recommendations), 2)
        self.assertEqual(
            recommendations[0].target_layer,
            "scoring_semantic_consistency_engine",
        )
        self.assertEqual(
            recommendations[1].target_layer,
            "commercial_lifecycle_analyzer",
        )
        self.assertTrue(recommendations[0].recommendation_key.startswith("case-001:"))

    def test_summarize_validation_gaps_returns_gap_summary(self) -> None:
        comparisons = (
            ValidationComparison(
                sample_id="case-001",
                human_baseline="人工结果",
                strong_agent_result="强智能体结果",
                target_agent_result="目标结果",
                gap_points=("评分问题漏判",),
            ),
            ValidationComparison(
                sample_id="case-002",
                human_baseline="人工结果",
                strong_agent_result="强智能体结果",
                target_agent_result="目标结果",
                gap_points=("边界问题误报",),
            ),
        )

        summary = summarize_validation_gaps(comparisons)

        self.assertEqual(summary["comparison_count"], 2)
        self.assertEqual(summary["gap_count"], 2)
        self.assertEqual(summary["sample_ids"], ("case-001", "case-002"))


if __name__ == "__main__":
    unittest.main()
