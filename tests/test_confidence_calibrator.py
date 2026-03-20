from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.core.knowledge.procurement_catalog import CatalogClassification
from agent_compliance.agents.compliance_review.pipelines.confidence_calibrator import calibrate_finding_confidence
from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import DEFAULT_STAGE_PROFILE
from agent_compliance.core.schemas import Finding


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

    def test_pre_release_stage_keeps_boundary_findings_at_least_medium(self) -> None:
        finding = Finding(
            finding_id="F-002A",
            document_name="sample.docx",
            problem_title="验收标准表述模糊且需发布前复核",
            page_hint=None,
            clause_id="2A",
            source_section="验收",
            section_path="验收要求",
            table_or_item_label=None,
            text_line_start=2,
            text_line_end=2,
            source_text="验收标准以采购人实际使用要求为准。",
            issue_type="unclear_acceptance_standard",
            risk_level="medium",
            severity_score=2,
            confidence="low",
            compliance_judgment="needs_human_review",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis=None,
            rewrite_suggestion="x",
            needs_human_review=True,
            human_review_reason="发布前应明确验收边界。",
            primary_authority=None,
        )
        self.assertEqual(
            calibrate_finding_confidence(finding, stage_profile=DEFAULT_STAGE_PROFILE),
            "medium",
        )

    def test_calibrator_uses_catalog_profile_high_risk_patterns(self) -> None:
        finding = Finding(
            finding_id="F-003",
            document_name="sports.docx",
            problem_title="技术评分权重过高且负偏离、专项检测加分进一步放大结构失衡",
            page_hint=None,
            clause_id="3",
            source_section="评分",
            section_path="评标信息",
            table_or_item_label=None,
            text_line_start=3,
            text_line_end=3,
            source_text="技术部分满分78分，价格部分满分10分，提供CMA或CNAS检测报告得分。",
            issue_type="scoring_structure_imbalance",
            risk_level="high",
            severity_score=2,
            confidence="medium",
            compliance_judgment="potentially_problematic",
            why_it_is_risky="命中体育器材及运动场设施画像中的技术评分过高与专项检测报告加分高风险模式。",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis=None,
            rewrite_suggestion="x",
            needs_human_review=False,
            human_review_reason=None,
        )
        classification = CatalogClassification(
            primary_catalog="CAT-SPORTS",
            primary_catalog_name="体育器材及运动场设施",
            primary_domain_key="sports_facility_goods",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=("A0321",),
            primary_mapped_catalog_prefixes=("A0321",),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="mixed",
            catalog_confidence=0.9,
            is_mixed_scope=False,
            catalog_evidence=("全民健身",),
        )
        self.assertEqual(calibrate_finding_confidence(finding, classification=classification), "high")

    def test_pre_release_stage_caps_justify_findings_at_medium(self) -> None:
        finding = Finding(
            finding_id="F-004",
            document_name="sample.docx",
            problem_title="技术要求可能合理但需补充必要性论证",
            page_hint=None,
            clause_id="4",
            source_section="技术",
            section_path="技术要求",
            table_or_item_label=None,
            text_line_start=4,
            text_line_end=4,
            source_text="需由本地机构出具检测报告。",
            issue_type="technical_justification_needed",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="needs_human_review",
            why_it_is_risky="需结合市场可得性补充论证。",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="x",
            rewrite_suggestion="x",
            needs_human_review=True,
            human_review_reason="x",
            primary_authority="《政府采购需求管理办法》第七条",
        )
        self.assertEqual(
            calibrate_finding_confidence(finding, stage_profile=DEFAULT_STAGE_PROFILE),
            "medium",
        )

    def test_pre_release_stage_keeps_direct_modify_authority_backed_finding_high(self) -> None:
        finding = Finding(
            finding_id="F-005",
            document_name="sample.docx",
            problem_title="商务责任和违约后果设置明显偏重",
            page_hint=None,
            clause_id="5",
            source_section="商务",
            section_path="商务条款",
            table_or_item_label=None,
            text_line_start=5,
            text_line_end=5,
            source_text="采购人不承担任何责任。",
            issue_type="one_sided_commercial_term",
            risk_level="high",
            severity_score=3,
            confidence="medium",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="责任条款绝对化。",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis="x",
            rewrite_suggestion="x",
            needs_human_review=False,
            human_review_reason=None,
            primary_authority="《民法典》相关规定",
        )
        self.assertEqual(
            calibrate_finding_confidence(finding, stage_profile=DEFAULT_STAGE_PROFILE),
            "high",
        )


if __name__ == "__main__":
    unittest.main()
