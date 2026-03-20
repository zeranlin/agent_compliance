from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.comparison_builder import (
    build_validation_comparison,
    build_validation_comparison_from_files,
)


class ComparisonBuilderTests(unittest.TestCase):
    def test_build_validation_comparison_extracts_aligned_and_gap_points(self) -> None:
        comparison = build_validation_comparison(
            sample_id="case-001",
            human_baseline="\n".join(
                [
                    "1. 输出项目概述和采购标的说明",
                    "2. 输出技术需求框架和验收需求框架",
                    "3. 输出待人工补充项",
                ]
            ),
            strong_agent_result="建议先给出结构化需求初稿骨架和待补充项。",
            target_agent_result="\n".join(
                [
                    "项目概述和采购标的说明",
                    "输出待人工补充项",
                ]
            ),
        )

        self.assertEqual(comparison.sample_id, "case-001")
        self.assertGreaterEqual(len(comparison.aligned_points), 1)
        self.assertIn("输出技术需求框架和验收需求框架", comparison.gap_points)
        self.assertTrue(comparison.summary)

    def test_build_validation_comparison_from_files_reads_texts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            human_path = temp_path / "human.txt"
            strong_path = temp_path / "strong.txt"
            target_path = temp_path / "target.txt"
            human_path.write_text("输出项目概述\n输出预算约束", encoding="utf-8")
            strong_path.write_text("建议输出结构化采购需求骨架", encoding="utf-8")
            target_path.write_text("输出项目概述", encoding="utf-8")

            comparison = build_validation_comparison_from_files(
                sample_id="case-002",
                human_baseline_path=human_path,
                strong_agent_result_path=strong_path,
                target_agent_result_path=target_path,
            )

        self.assertEqual(comparison.sample_id, "case-002")
        self.assertIn("输出预算约束", comparison.gap_points)


if __name__ == "__main__":
    unittest.main()
