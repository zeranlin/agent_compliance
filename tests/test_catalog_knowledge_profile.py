from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.knowledge.catalog_knowledge_profile import (
    catalog_commercial_lifecycle_markers_for_classification,
    catalog_core_delivery_capabilities_for_classification,
    catalog_domain_mismatch_markers_for_classification,
    catalog_mixed_scope_core_markers_for_classification,
    catalog_scoring_evidence_markers_for_classification,
    catalog_mixed_scope_markers_for_classification,
    catalog_mixed_scope_out_of_scope_markers_for_classification,
    catalog_knowledge_profile_by_catalog_id,
    catalog_knowledge_profiles_for_classification,
    catalog_scoring_mismatch_markers_for_classification,
    catalog_scoring_risk_markers_for_classification,
    catalog_scoring_theme_markers_for_classification,
    catalog_template_scope_markers_for_classification,
    load_catalog_knowledge_profiles,
)
from agent_compliance.knowledge.procurement_catalog import CatalogClassification
from agent_compliance.pipelines.review_strategy import build_document_strategy_profile


class CatalogKnowledgeProfileTest(unittest.TestCase):
    def test_load_catalog_knowledge_profiles(self) -> None:
        profiles = load_catalog_knowledge_profiles()
        self.assertGreaterEqual(len(profiles), 10)
        furniture = catalog_knowledge_profile_by_catalog_id("CAT-FURNITURE")
        self.assertIsNotNone(furniture)
        assert furniture is not None
        self.assertIn("环保要求", furniture.reasonable_requirements)
        self.assertIn("供货质量", furniture.core_delivery_capabilities)
        self.assertIn("智能管理边界外扩", furniture.high_risk_patterns)
        self.assertIn("生产设备", furniture.scoring_risk_markers)
        self.assertIn("供货质量", furniture.scoring_theme_markers)
        self.assertIn("供货方案", furniture.scoring_evidence_markers)
        self.assertTrue(furniture.boundary_notes)
        sports = catalog_knowledge_profile_by_catalog_id("CAT-SPORTS")
        self.assertIsNotNone(sports)
        assert sports is not None
        self.assertIn("技术评分过高", sports.high_risk_patterns)
        self.assertIn("器材供货", sports.core_delivery_capabilities)
        self.assertIn("二维码报修系统", sports.common_mismatch_clues)
        self.assertIn("二维码报修系统", sports.domain_mismatch_markers)
        self.assertIn("二维码报修系统", sports.template_scope_markers)
        self.assertIn("智能显示", sports.mixed_scope_markers)
        self.assertIn("运动场", sports.mixed_scope_core_markers)
        self.assertIn("二维码报修系统", sports.mixed_scope_out_of_scope_markers)

    def test_profiles_follow_classification(self) -> None:
        classification = CatalogClassification(
            primary_catalog="CAT-MEDICAL-TCM",
            primary_catalog_name="药品及医用配套",
            primary_domain_key="medical_tcm_mixed",
            secondary_catalogs=("CAT-INFO",),
            secondary_catalog_names=("信息化平台及系统运维",),
            primary_mapped_catalog_codes=("A1101",),
            primary_mapped_catalog_prefixes=("A1101",),
            secondary_mapped_catalog_codes=("C1602",),
            secondary_mapped_catalog_prefixes=("C1602",),
            category_type="mixed",
            catalog_confidence=0.9,
            is_mixed_scope=True,
            catalog_evidence=("中药配方颗粒", "信息化管理系统"),
        )
        profiles = catalog_knowledge_profiles_for_classification(classification)
        profile_ids = {item.catalog_id for item in profiles}
        self.assertIn("CAT-MEDICAL-TCM", profile_ids)
        self.assertIn("CAT-INFO", profile_ids)
        self.assertIn("信息化管理系统", catalog_mixed_scope_markers_for_classification(classification))
        self.assertIn("中药配方颗粒", catalog_mixed_scope_core_markers_for_classification(classification))
        self.assertIn("信息化管理系统", catalog_mixed_scope_out_of_scope_markers_for_classification(classification))
        self.assertIn("园区保洁", catalog_template_scope_markers_for_classification(classification))
        self.assertIn("药品供货", catalog_core_delivery_capabilities_for_classification(classification))
        self.assertIn("信息化管理系统", catalog_scoring_risk_markers_for_classification(classification))
        self.assertIn("药品供货", catalog_scoring_theme_markers_for_classification(classification))
        self.assertIn("配送方案", catalog_scoring_evidence_markers_for_classification(classification))
        self.assertIn("36个月", catalog_commercial_lifecycle_markers_for_classification(classification))

    def test_strategy_profile_consumes_catalog_knowledge(self) -> None:
        classification = CatalogClassification(
            primary_catalog="CAT-SIGNAGE",
            primary_catalog_name="标识标牌及宣传印制",
            primary_domain_key="signage_printing_service",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=("C23150000",),
            primary_mapped_catalog_prefixes=("C2315",),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="service",
            catalog_confidence=0.92,
            is_mixed_scope=False,
            catalog_evidence=("标识标牌",),
        )
        strategy = build_document_strategy_profile([], classification=classification)
        self.assertIn("设计制作", strategy.catalog_reasonable_requirements)
        self.assertIn("设计制作", strategy.catalog_core_delivery_capabilities)
        self.assertIn("错位IT/保安/信息安全认证", strategy.catalog_high_risk_patterns)
        self.assertTrue(strategy.catalog_boundary_notes)
        self.assertIn("scoring", strategy.preferred_analyzer_groups)

    def test_domain_mismatch_markers_follow_classification(self) -> None:
        classification = CatalogClassification(
            primary_catalog="CAT-SIGNAGE",
            primary_catalog_name="标识标牌及宣传印制",
            primary_domain_key="signage_printing_service",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=("C23150000",),
            primary_mapped_catalog_prefixes=("C2315",),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="service",
            catalog_confidence=0.92,
            is_mixed_scope=False,
            catalog_evidence=("标识标牌",),
        )
        markers = catalog_domain_mismatch_markers_for_classification(classification)
        self.assertIn("IT服务管理体系认证", markers)
        self.assertIn("交通部交工验收", markers)
        scoring_markers = catalog_scoring_mismatch_markers_for_classification(classification)
        self.assertIn("软件著作权", scoring_markers)
        self.assertIn("设计制作", catalog_scoring_theme_markers_for_classification(classification))
        self.assertIn("设计方案", catalog_scoring_evidence_markers_for_classification(classification))


if __name__ == "__main__":
    unittest.main()
