from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.pipelines.procurement_stage_router import DEFAULT_STAGE_PROFILE
from agent_compliance.pipelines.rewrite_generator import (
    ACTION_DIRECT,
    ACTION_JUSTIFY,
    ACTION_REVIEW,
    apply_rewrite_generator,
    determine_suggested_action,
)
from agent_compliance.schemas import Finding


class RewriteGeneratorTest(unittest.TestCase):
    def test_direct_modify_prefix_is_added_for_high_risk_commercial_finding(self) -> None:
        finding = Finding(
            finding_id="F-001",
            document_name="sample.docx",
            problem_title="商务责任和违约后果设置明显偏重",
            page_hint=None,
            clause_id="1",
            source_section="商务",
            section_path="商务条款",
            table_or_item_label=None,
            text_line_start=1,
            text_line_end=1,
            source_text="采购人不承担任何责任。",
            issue_type="one_sided_commercial_term",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="责任条款绝对化。",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="x",
            rewrite_suggestion="按过错和责任来源划分责任。",
            needs_human_review=False,
            human_review_reason=None,
        )
        self.assertEqual(determine_suggested_action(finding, stage_profile=DEFAULT_STAGE_PROFILE), ACTION_DIRECT)
        updated = apply_rewrite_generator([finding], stage_profile=DEFAULT_STAGE_PROFILE)[0]
        self.assertTrue(updated.rewrite_suggestion.startswith("建议直接修改："))

    def test_technical_justification_finding_is_marked_as_justify(self) -> None:
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
            confidence="medium",
            compliance_judgment="needs_human_review",
            why_it_is_risky="需补论证。",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="x",
            rewrite_suggestion="改成以有效证明材料证明。",
            needs_human_review=True,
            human_review_reason=None,
        )
        self.assertEqual(determine_suggested_action(finding, stage_profile=DEFAULT_STAGE_PROFILE), ACTION_JUSTIFY)
        updated = apply_rewrite_generator([finding], stage_profile=DEFAULT_STAGE_PROFILE)[0]
        self.assertTrue(updated.rewrite_suggestion.startswith("建议补充必要性论证："))
        self.assertIsNotNone(updated.human_review_reason)

    def test_boundary_human_review_finding_is_marked_as_review(self) -> None:
        finding = Finding(
            finding_id="F-003",
            document_name="sample.docx",
            problem_title="模板条款与当前采购边界不完全一致",
            page_hint=None,
            clause_id="3",
            source_section="技术",
            section_path="技术要求",
            table_or_item_label=None,
            text_line_start=3,
            text_line_end=3,
            source_text="系统端口无缝对接。",
            issue_type="template_mismatch",
            risk_level="medium",
            severity_score=2,
            confidence="medium",
            compliance_judgment="needs_human_review",
            why_it_is_risky="边界不清。",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis=None,
            rewrite_suggestion="删除无关接口要求。",
            needs_human_review=True,
            human_review_reason=None,
        )
        self.assertEqual(determine_suggested_action(finding, stage_profile=DEFAULT_STAGE_PROFILE), ACTION_REVIEW)
        updated = apply_rewrite_generator([finding], stage_profile=DEFAULT_STAGE_PROFILE)[0]
        self.assertTrue(updated.rewrite_suggestion.startswith("建议采购/法务复核："))
        self.assertIn("发布前建议", updated.human_review_reason or "")


if __name__ == "__main__":
    unittest.main()
