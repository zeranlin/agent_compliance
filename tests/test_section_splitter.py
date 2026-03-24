from __future__ import annotations

import unittest

from agent_compliance.core.parsers.section_splitter import split_into_clauses


class SectionSplitterTests(unittest.TestCase):
    def test_percent_text_is_not_recognized_as_section_heading(self) -> None:
        text = "\n".join(
            [
                "一、项目需求及分包情况、采购标的",
                "0.00 %；",
                "付款方式：按合同约定执行。",
            ]
        )
        clauses = split_into_clauses(text)
        self.assertEqual(clauses[0].source_section, "一、项目需求及分包情况、采购标的")
        self.assertEqual(clauses[1].source_section, "一、项目需求及分包情况、采购标的")
        self.assertEqual(clauses[1].section_path, "一、项目需求及分包情况、采购标的")

    def test_decimal_table_value_is_not_recognized_as_section_heading(self) -> None:
        text = "\n".join(
            [
                "四、项目需求及分包情况、采购标的",
                "2.00 是",
                "付款方式：按合同约定执行。",
            ]
        )
        clauses = split_into_clauses(text)
        self.assertEqual(clauses[1].source_section, "四、项目需求及分包情况、采购标的")
        self.assertEqual(clauses[1].section_path, "四、项目需求及分包情况、采购标的")

    def test_table_header_row_is_not_recognized_as_section_heading(self) -> None:
        text = "\n".join(
            [
                "四、项目需求及分包情况、采购标的",
                "序号 资格要求名称 资格要求详细说明",
                "付款方式：按合同约定执行。",
            ]
        )
        clauses = split_into_clauses(text)
        self.assertEqual(clauses[1].source_section, "四、项目需求及分包情况、采购标的")
        self.assertEqual(clauses[1].section_path, "四、项目需求及分包情况、采购标的")


if __name__ == "__main__":
    unittest.main()
