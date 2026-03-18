from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.pipelines.confidence_calibrator import calibrate_finding_confidence
from agent_compliance.schemas import Finding


class ConfidenceCalibratorTest(unittest.TestCase):
    def test_calibrator_keeps_authority_backed_high_risk_finding_high(self) -> None:
        finding = Finding(
            finding_id="F-001",
            document_name="sample.docx",
            problem_title="资格条件设置一般门槛",
            page_hint=None,
            clause_id="1",
            source_section="资格",
            section_path="资格条件",
            table_or_item_label=None,
            text_line_start=1,
            text_line_end=1,
            source_text="注册资本不低于5000万。",
            issue_type="excessive_supplier_qualification",
            risk_level="high",
            severity_score=3,
            confidence="medium",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="x",
            rewrite_suggestion="x",
            needs_human_review=False,
            human_review_reason=None,
            primary_authority="《政府采购需求管理办法》第十八条、第三十一条",
        )
        self.assertEqual(calibrate_finding_confidence(finding), "high")

    def test_calibrator_keeps_human_review_boundary_issue_medium(self) -> None:
        finding = Finding(
            finding_id="F-002",
            document_name="sample.docx",
            problem_title="技术要求可能合理但需补充必要性论证",
            page_hint=None,
            clause_id="2",
            source_section="技术",
            section_path="技术要求",
            table_or_item_label=None,
            text_line_start=2,
            text_line_end=2,
            source_text="检测报告须由本地机构出具。",
            issue_type="technical_justification_needed",
            risk_level="medium",
            severity_score=2,
            confidence="high",
            compliance_judgment="needs_human_review",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="x",
            rewrite_suggestion="x",
            needs_human_review=True,
            human_review_reason="法规侧复核重点：需核查法定必要性。",
            primary_authority="《政府采购需求管理办法》第七条、第九条",
        )
        self.assertEqual(calibrate_finding_confidence(finding), "medium")


if __name__ == "__main__":
    unittest.main()
