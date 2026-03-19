from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.pipelines.effective_requirement_scope_filter import (
    REQUIREMENT_SCOPE_BODY,
    REQUIREMENT_SCOPE_FORMAT,
    REQUIREMENT_SCOPE_HINT,
    REQUIREMENT_SCOPE_TEMPLATE,
    classify_clause_scope,
    classify_requirement_scope,
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


if __name__ == "__main__":
    unittest.main()
