from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.requirement_definition import (
    build_requirement_definition,
    build_requirement_guidance,
    infer_template_key,
    render_requirement_definition_markdown,
    write_requirement_definition,
)


class RequirementDefinitionTests(unittest.TestCase):
    def test_infer_template_key_prefers_review_for_checking_need(self) -> None:
        self.assertEqual(
            infer_template_key(
                business_need="我要一个合规性检查智能体，用来对政府采购采购需求文档发布前进行风险检查",
                usage_scenario="采购人内部发布前复核",
            ),
            "review",
        )

    def test_build_requirement_guidance_generates_process_and_questions(self) -> None:
        guidance = build_requirement_guidance(
            agent_name="",
            business_need="根据采购品目和预算生成采购需求初稿骨架",
            usage_scenario="采购需求编制前的需求调研阶段",
        )
        self.assertEqual(guidance.template_key, "budget_analysis")
        self.assertEqual(len(guidance.handling_process), 6)
        self.assertGreaterEqual(len(guidance.clarification_questions), 3)
        self.assertIn("预算", guidance.product_direction)

    def test_build_requirement_definition_generates_summary_fields(self) -> None:
        draft = build_requirement_definition(
            agent_name="政府采购采购需求调查智能体",
            template_key="demand_research",
            business_need="根据采购品目和预算生成采购需求初稿骨架",
            usage_scenario="采购人发布采购文件前的内部准备阶段",
            user_roles=("采购人", "法务复核人员"),
            input_documents=("采购品目", "预算金额"),
            expected_outputs=("采购需求初稿", "待补充项"),
            success_criteria=("能输出结构化章节", "能明确待补充项"),
            non_goals=("不直接替代法务签发",),
            constraints=("需支持本地运行",),
        )
        self.assertEqual(draft.template_key, "demand_research")
        self.assertIn("采购人", draft.product_definition)
        self.assertIn("第一版先做到", draft.first_version_goal)
        self.assertEqual(len(draft.capability_boundary), 4)

    def test_write_requirement_definition_outputs_json_and_markdown(self) -> None:
        draft = build_requirement_definition(
            agent_name="政府采购四类专项检查智能体",
            template_key="review",
            business_need="输出四类专项检查结论和整改建议",
            usage_scenario="采购文件专项检查前置复核",
            user_roles=("采购人",),
            input_documents=("采购文件",),
            expected_outputs=("专项检查结论",),
            success_criteria=("能输出统一专项结论模板",),
        )
        markdown = render_requirement_definition_markdown(draft)
        self.assertIn("需求定义确认稿", markdown)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_requirement_definition(Path(tmpdir), draft)
            self.assertTrue(paths.json_path.exists())
            self.assertTrue(paths.markdown_path.exists())
            self.assertIn("产品定义", paths.markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
