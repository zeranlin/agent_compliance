from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.knowledge.legal_authority_reasoner import reason_for_finding
from agent_compliance.schemas import Finding


class LegalAuthorityReasonerTest(unittest.TestCase):
    def test_reasoner_generates_primary_secondary_basis_and_logic(self) -> None:
        finding = Finding(
            finding_id="F-001",
            document_name="sample.docx",
            problem_title="评分内容与评分主题不一致",
            page_hint=None,
            clause_id="C-001",
            source_section="评标信息",
            section_path="第一章-评标信息-商务部分",
            table_or_item_label="评分因素",
            text_line_start=10,
            text_line_end=12,
            source_text="投标人具有与本项目无关的认证证书得分。",
            issue_type="scoring_content_mismatch",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis=None,
            rewrite_suggestion="x",
            needs_human_review=False,
            human_review_reason=None,
        )

        reasoning = reason_for_finding(finding)
        self.assertIsNotNone(reasoning)
        assert reasoning is not None
        self.assertIn("政府采购需求管理办法", reasoning.primary_authority or "")
        self.assertTrue(reasoning.secondary_authorities)
        self.assertIn("评分因素", reasoning.applicability_logic or "")
        self.assertIn("主依据：", reasoning.legal_or_policy_basis or "")
        self.assertTrue(reasoning.needs_human_review)
        self.assertIn("法规侧复核重点", reasoning.human_review_reason or "")

    def test_reasoner_preserves_existing_basis_text(self) -> None:
        finding = Finding(
            finding_id="F-002",
            document_name="sample.docx",
            problem_title="资格条件设置一般门槛",
            page_hint=None,
            clause_id="C-002",
            source_section="资格条件",
            section_path="第一章-资格条件",
            table_or_item_label=None,
            text_line_start=2,
            text_line_end=3,
            source_text="供应商注册资本不低于5000万元。",
            issue_type="excessive_supplier_qualification",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="政府采购需求管理办法（财政部）",
            rewrite_suggestion="x",
            needs_human_review=False,
            human_review_reason=None,
        )

        reasoning = reason_for_finding(finding)
        self.assertIsNotNone(reasoning)
        assert reasoning is not None
        self.assertIn("政府采购需求管理办法（财政部）", reasoning.legal_or_policy_basis or "")
        self.assertIn("主依据：", reasoning.legal_or_policy_basis or "")


if __name__ == "__main__":
    unittest.main()
