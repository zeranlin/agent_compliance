from __future__ import annotations

import unittest

from agent_compliance.incubator.lifecycle import ValidationComparison
from agent_compliance.incubator.regression_runner import build_regression_feedback


class RegressionRunnerTests(unittest.TestCase):
    def test_build_regression_feedback_detects_gap_reduction(self) -> None:
        previous = ValidationComparison(
            sample_id="case-001",
            human_baseline="人工",
            strong_agent_result="强智能体",
            target_agent_result="旧目标智能体",
            aligned_points=("输出项目概述",),
            gap_points=("输出技术需求框架", "输出验收需求框架"),
        )
        current = ValidationComparison(
            sample_id="case-001",
            human_baseline="人工",
            strong_agent_result="强智能体",
            target_agent_result="新目标智能体",
            aligned_points=("输出项目概述", "输出技术需求框架"),
            gap_points=("输出验收需求框架",),
        )

        feedback = build_regression_feedback(previous, current)

        self.assertIn("差异点已从 2 个下降到 1 个", feedback.regression_result)
        self.assertIn("剩余差异压缩到 1 个", feedback.capability_change)

    def test_build_regression_feedback_handles_first_regression_record(self) -> None:
        current = ValidationComparison(
            sample_id="case-002",
            human_baseline="人工",
            strong_agent_result="强智能体",
            target_agent_result="新目标智能体",
            aligned_points=("输出项目概述",),
            gap_points=("输出预算约束",),
        )

        feedback = build_regression_feedback(None, current)

        self.assertIn("已记录", feedback.regression_result)
        self.assertIn("仍剩 1 个差异点", feedback.capability_change)


if __name__ == "__main__":
    unittest.main()
