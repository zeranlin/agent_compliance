from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.pipelines.effective_requirement_scope_filter import (
    REQUIREMENT_SCOPE_BODY,
    REQUIREMENT_SCOPE_FORMAT,
    REQUIREMENT_SCOPE_HINT,
    REQUIREMENT_SCOPE_TEMPLATE,
    annotate_document_requirement_scope,
    classify_clause_scope,
    classify_requirement_scope,
)
from agent_compliance.pipelines.requirement_scope_layer import (
    EFFECT_REFERENCE_ONLY,
    EFFECT_STRONG_BINDING,
    FUNCTION_REFERENCE_NOTE,
    FUNCTION_SCORING_EVIDENCE,
    SCOPE_BACKGROUND_TEXT,
    SCOPE_SCORING_RULE,
)


class EffectiveRequirementScopeFilterTest(unittest.TestCase):
    def test_classify_platform_warning_as_hint(self) -> None:
        result = classify_requirement_scope(
            section_path="第四章-投标文件组成要求及格式",
            text="特别警示条款：投标文件制作工具会记录文件创建标识码和制作机器码。",
        )
        self.assertEqual(result.category, REQUIREMENT_SCOPE_HINT)

    def test_classify_format_instruction_as_format(self) -> None:
        result = classify_requirement_scope(
            section_path="第四章-投标文件组成要求及格式",
            text="投标文件正文（信息公开部分）格式自定，按填写说明编制。",
        )
        self.assertEqual(result.category, REQUIREMENT_SCOPE_FORMAT)

    def test_classify_commitment_letter_as_template(self) -> None:
        result = classify_requirement_scope(
            section_path="第四章-政府采购投标及履约承诺函",
            text="政府采购投标及履约承诺函",
        )
        self.assertEqual(result.category, REQUIREMENT_SCOPE_TEMPLATE)

    def test_classify_real_requirement_as_body(self) -> None:
        clauses = split_into_clauses(
            "\n".join(
                [
                    "第三章 用户需求书",
                    "中标人应负责设备供货、安装、调试并完成验收。",
                ]
            )
        )
        self.assertEqual(classify_clause_scope(clauses[1]).category, REQUIREMENT_SCOPE_BODY)

    def test_classify_scoring_clause_with_evidence_and_effect_strength(self) -> None:
        result = classify_requirement_scope(
            section_path="评标信息-评分项-技术部分-评分因素",
            text="提供检测报告且检测报告委托单位须为投标人，可得5分。",
        )
        self.assertEqual(result.scope_type, SCOPE_SCORING_RULE)
        self.assertEqual(result.clause_function, FUNCTION_SCORING_EVIDENCE)
        self.assertEqual(result.effect_strength, EFFECT_STRONG_BINDING)
        self.assertTrue(result.is_high_weight_requirement)

    def test_classify_note_as_background_reference_only(self) -> None:
        result = classify_requirement_scope(
            section_path="第三章 用户需求书-说明",
            text="说明：以上参数为参考写法，采购人可结合实际调整。",
        )
        self.assertEqual(result.scope_type, SCOPE_BACKGROUND_TEXT)
        self.assertEqual(result.clause_function, FUNCTION_REFERENCE_NOTE)
        self.assertEqual(result.effect_strength, EFFECT_REFERENCE_ONLY)
        self.assertFalse(result.is_high_weight_requirement)

    def test_annotate_document_requirement_scope_sets_clause_fields(self) -> None:
        clauses = split_into_clauses(
            "\n".join(
                [
                    "评标信息",
                    "评分因素",
                    "提供检测报告且检测报告委托单位须为投标人，可得5分。",
                ]
            )
        )
        document = type("Doc", (), {"clauses": clauses})()
        annotate_document_requirement_scope(document)
        self.assertEqual(clauses[2].scope_type, SCOPE_SCORING_RULE)
        self.assertEqual(clauses[2].clause_function, FUNCTION_SCORING_EVIDENCE)
        self.assertEqual(clauses[2].effect_strength, EFFECT_STRONG_BINDING)
        self.assertTrue(clauses[2].is_effective_requirement)


if __name__ == "__main__":
    unittest.main()
