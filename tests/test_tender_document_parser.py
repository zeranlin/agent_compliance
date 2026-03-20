from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.core.parsers.section_splitter import split_into_clauses
from agent_compliance.core.pipelines.tender_document_parser import (
    TENDER_PARSER_MODE_ASSIST,
    TENDER_PARSER_MODE_OFF,
    TENDER_PARSER_MODE_REQUIRED,
    clause_in_structured_sections,
    collect_structured_clause_ids,
    parse_tender_document,
    prepare_review_document,
    resolve_tender_parser_mode,
)
from agent_compliance.core.pipelines.tender_document_risk_scope_layer import RISK_SCOPE_CORE, STRUCTURE_SCORING_RULES
from agent_compliance.core.schemas import NormalizedDocument


def _build_document(text: str) -> NormalizedDocument:
    clauses = split_into_clauses(text)
    return NormalizedDocument(
        source_path="/tmp/test.docx",
        document_name="test.docx",
        file_hash="abc123",
        normalized_text_path="/tmp/test.txt",
        clause_count=len(clauses),
        clauses=clauses,
    )


class TenderDocumentParserTest(unittest.TestCase):
    def test_resolve_mode_defaults_to_off_for_unknown_value(self) -> None:
        self.assertEqual(resolve_tender_parser_mode("weird"), TENDER_PARSER_MODE_OFF)

    def test_parse_tender_document_groups_core_and_supporting_sections(self) -> None:
        document = _build_document(
            "\n".join(
                [
                    "第二章 投标人须知",
                    "投标文件组成要求及格式",
                    "第三章 评标信息",
                    "评分因素",
                    "提供检测报告得5分。",
                    "第四章 用户需求书",
                    "技术要求",
                    "中标人应完成供货、安装、调试。",
                ]
            )
        )
        structured = parse_tender_document(document, parser_mode=TENDER_PARSER_MODE_ASSIST)
        self.assertGreaterEqual(structured.section_count, 2)
        self.assertGreaterEqual(structured.core_section_count, 1)
        self.assertGreaterEqual(structured.supporting_section_count, 1)

    def test_prepare_review_document_required_mode_needs_core_sections(self) -> None:
        document = _build_document(
            "\n".join(
                [
                    "附件",
                    "投标函",
                    "我单位承诺如下。",
                ]
            )
        )
        with self.assertRaises(ValueError):
            prepare_review_document(document, parser_mode=TENDER_PARSER_MODE_REQUIRED)

    def test_structured_section_helpers_can_pick_scoring_clauses(self) -> None:
        document = _build_document(
            "\n".join(
                [
                    "评标信息",
                    "评分因素",
                    "提供检测报告得5分。",
                    "技术要求",
                    "中标人应完成供货、安装、调试。",
                ]
            )
        )
        structured = parse_tender_document(document, parser_mode=TENDER_PARSER_MODE_ASSIST)
        scoring_ids = collect_structured_clause_ids(
            structured,
            structure_types=(STRUCTURE_SCORING_RULES,),
            risk_scopes=(RISK_SCOPE_CORE,),
        )
        self.assertTrue(scoring_ids)
        self.assertTrue(
            clause_in_structured_sections(
                document.clauses[1],
                structured,
                structure_types=(STRUCTURE_SCORING_RULES,),
                risk_scopes=(RISK_SCOPE_CORE,),
            )
        )


if __name__ == "__main__":
    unittest.main()
