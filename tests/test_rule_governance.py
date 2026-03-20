from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.core.knowledge.procurement_catalog import CatalogClassification
from agent_compliance.core.knowledge.rule_registry import build_rule_registry, load_rule_priority_profile, rule_registry_map
from agent_compliance.agents.compliance_review.pipelines.catalog_sensitive_rule_router import route_rules_for_catalog
from agent_compliance.core.parsers.section_splitter import split_into_clauses
from agent_compliance.agents.compliance_review.pipelines.rule_scan import run_rule_scan
from agent_compliance.core.schemas import NormalizedDocument


class RuleGovernanceTest(unittest.TestCase):
    def test_rule_registry_covers_formal_rule_set(self) -> None:
        registry = build_rule_registry()
        rule_ids = {item.rule_id for item in registry}
        self.assertIn("QUAL-001", rule_ids)
        self.assertIn("SCORE-010", rule_ids)
        self.assertIn("TECH-003", rule_ids)
        self.assertIn("CONTRACT-014", rule_ids)

    def test_rule_priority_profile_loads_domain_overrides(self) -> None:
        profile = load_rule_priority_profile()
        self.assertEqual(profile.default_family_priorities["scoring"], 90)
        self.assertEqual(profile.domain_profiles["information_system"]["family_priorities"]["scoring"], 115)
        self.assertEqual(profile.domain_profiles["property_service"]["family_priorities"]["commercial"], 115)
        self.assertIn("SCORE-015", profile.domain_profiles["property_service"]["disabled_rule_ids"])
        self.assertIn("qualification_domain_mismatch", profile.domain_profiles["property_service"]["deprioritized_issue_types"])

    def test_rule_registry_exposes_governance_status_layers(self) -> None:
        registry = rule_registry_map()
        self.assertEqual(registry["QUAL-001"].rule_status, "formal_active")
        self.assertEqual(registry["QUAL-013"].rule_status, "formal_catalog_sensitive")
        self.assertEqual(registry["SCORE-002"].rule_status, "formal_support")
        self.assertTrue(registry["SCORE-002"].enabled_by_default)

    def test_catalog_sensitive_router_boosts_information_system_scoring_rules(self) -> None:
        classification = CatalogClassification(
            primary_catalog="CAT-INFO",
            primary_catalog_name="信息化平台及系统运维",
            primary_domain_key="information_system",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=("C16020000",),
            primary_mapped_catalog_prefixes=("C1602",),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="service",
            catalog_confidence=0.95,
            is_mixed_scope=False,
            catalog_evidence=("信息系统集成实施服务",),
        )
        routed = route_rules_for_catalog(classification)
        top_rule_ids = [item.rule.rule_id for item in routed[:8]]
        self.assertIn("SCORE-010", top_rule_ids)

    def test_catalog_sensitive_router_supports_disable_and_deweight(self) -> None:
        classification = CatalogClassification(
            primary_catalog="CAT-PROPERTY",
            primary_catalog_name="物业管理服务",
            primary_domain_key="property_service",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=("C21040000",),
            primary_mapped_catalog_prefixes=("C2104",),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="service",
            catalog_confidence=0.95,
            is_mixed_scope=False,
            catalog_evidence=("物业管理服务",),
        )
        routed = route_rules_for_catalog(classification)
        score015 = next(item for item in routed if item.rule.rule_id == "SCORE-015")
        qual013 = next(item for item in routed if item.rule.rule_id == "QUAL-013")
        self.assertFalse(score015.is_enabled)
        self.assertIn("显式停用", score015.route_reason)
        self.assertTrue(qual013.is_enabled)
        self.assertTrue(qual013.is_deweighted)
        self.assertIn("显式降权", qual013.route_reason)

    def test_rule_scan_keeps_highest_priority_rule_per_merge_key_on_same_clause(self) -> None:
        text = "\n".join(
            [
                "项目名称：基础服务体系平台运营项目",
                "评标信息",
                "投标人本地服务团队1小时内到达现场得满分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/info.docx",
            document_name="基础服务体系平台运营项目.docx",
            file_hash="info-1",
            normalized_text_path="/tmp/info.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        target_hits = [item for item in hits if item.line_start == clauses[-1].line_start and item.merge_key == "scoring-geographic"]
        self.assertEqual(len(target_hits), 1)
        self.assertEqual(target_hits[0].rule_id, "SCORE-010")

    def test_rule_scan_skips_disabled_rules_for_catalog(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院物业管理服务项目",
                "评标信息",
                "整体每延长1年免费质保期的得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/property.docx",
            document_name="医院物业管理服务项目.docx",
            file_hash="property-1",
            normalized_text_path="/tmp/property.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        self.assertFalse(any(item.rule_id == "SCORE-015" for item in hits))


if __name__ == "__main__":
    unittest.main()
