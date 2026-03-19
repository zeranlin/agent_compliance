from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.pipelines.tender_document_risk_scope_layer import (
    RISK_SCOPE_CORE,
    RISK_SCOPE_OUT,
    RISK_SCOPE_SUPPORTING,
    STRUCTURE_ATTACHMENTS_TEMPLATES,
    STRUCTURE_BIDDER_INSTRUCTIONS,
    STRUCTURE_SCORING_RULES,
    annotate_tender_document_risk_scope,
    classify_tender_document_risk_scope,
)


class TenderDocumentRiskScopeLayerTest(unittest.TestCase):
    def test_classify_scoring_rules_as_core_scope(self) -> None:
        clauses = split_into_clauses(
            "\n".join(
                [
                    "评标信息",
                    "评分因素",
                    "供应商提供检测报告的，得5分。",
                ]
            )
        )
        result = classify_tender_document_risk_scope(clauses[1])
        self.assertEqual(result.document_structure_type, STRUCTURE_SCORING_RULES)
        self.assertEqual(result.risk_scope, RISK_SCOPE_CORE)

    def test_classify_bidder_instructions_as_supporting_scope(self) -> None:
        clauses = split_into_clauses(
            "\n".join(
                [
                    "第二章 投标人须知",
                    "投标文件组成要求及格式",
                    "投标文件应按要求编制。",
                ]
            )
        )
        result = classify_tender_document_risk_scope(clauses[1])
        self.assertEqual(result.document_structure_type, STRUCTURE_BIDDER_INSTRUCTIONS)
        self.assertEqual(result.risk_scope, RISK_SCOPE_SUPPORTING)

    def test_classify_attachment_template_as_out_of_scope(self) -> None:
        clauses = split_into_clauses(
            "\n".join(
                [
                    "附件",
                    "政府采购投标及履约承诺函",
                    "我单位承诺如下。",
                ]
            )
        )
        result = classify_tender_document_risk_scope(clauses[1])
        self.assertEqual(result.document_structure_type, STRUCTURE_ATTACHMENTS_TEMPLATES)
        self.assertEqual(result.risk_scope, RISK_SCOPE_OUT)

    def test_annotate_document_sets_structure_and_risk_scope(self) -> None:
        clauses = split_into_clauses(
            "\n".join(
                [
                    "评标信息",
                    "评分因素",
                    "供应商提供检测报告的，得5分。",
                ]
            )
        )
        document = type("Doc", (), {"clauses": clauses})()
        annotate_tender_document_risk_scope(document)
        self.assertEqual(clauses[2].document_structure_type, STRUCTURE_SCORING_RULES)
        self.assertEqual(clauses[2].risk_scope, RISK_SCOPE_CORE)
        self.assertTrue(clauses[2].scope_reason)


if __name__ == "__main__":
    unittest.main()
