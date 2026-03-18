from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_compliance.knowledge.procurement_catalog import (
    classify_procurement_catalog,
    classification_has_catalog_prefix,
    full_catalog_names_by_code_or_prefix,
    load_procurement_catalogs,
)
from agent_compliance.knowledge.review_domain_map import load_review_domain_map
from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.pipelines.review_strategy import build_analyzer_execution_order, build_document_strategy_profile
from agent_compliance.schemas import NormalizedDocument
from tests._bootstrap import REPO_ROOT


class ProcurementCatalogTest(unittest.TestCase):
    def _document(self, name: str, lines: list[str]) -> NormalizedDocument:
        text = "\n".join(lines)
        clauses = split_into_clauses(text)
        return NormalizedDocument(
            source_path=f"/tmp/{name}",
            document_name=name,
            file_hash=name,
            normalized_text_path=f"/tmp/{name}.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

    def test_load_procurement_catalogs(self) -> None:
        catalogs = load_procurement_catalogs()
        self.assertGreaterEqual(len(catalogs), 10)
        self.assertTrue(any(item.domain_key == "information_system" for item in catalogs))
        info_catalog = next(item for item in catalogs if item.domain_key == "information_system")
        self.assertIn("信息系统集成实施服务", info_catalog.domain_keywords)

    def test_classify_sports_facility_project(self) -> None:
        document = self._document(
            "2025年省级全民健身工程（多功能运动场项目）.docx",
            ["全民健身工程", "多功能运动场", "围网", "硅PU", "体育比赛用灯", "二维码报修"],
        )
        classification = classify_procurement_catalog(document)

        self.assertEqual(classification.primary_domain_key, "sports_facility_goods")
        self.assertEqual(classification.primary_catalog_name, "体育器材及运动场设施")
        self.assertTrue(classification_has_catalog_prefix(classification, "A0246"))
        self.assertTrue(classification.is_mixed_scope)

    def test_classify_information_system_project(self) -> None:
        document = self._document(
            "民生诉求服务平台（二期）项目.docx",
            ["平台建设", "系统对接", "软件著作权", "驻场运维"],
        )
        classification = classify_procurement_catalog(document)

        self.assertEqual(classification.primary_domain_key, "information_system")
        self.assertEqual(classification.primary_catalog_name, "信息化平台及系统运维")
        self.assertTrue(classification_has_catalog_prefix(classification, "C1602"))
        self.assertFalse(classification.is_mixed_scope)

    def test_classify_by_official_catalog_name(self) -> None:
        document = self._document(
            "信息系统集成实施服务项目.docx",
            ["信息系统集成实施服务", "运行维护服务", "应用软件开发服务"],
        )
        classification = classify_procurement_catalog(document)

        self.assertEqual(classification.primary_domain_key, "information_system")
        self.assertEqual(classification.primary_catalog_name, "信息化平台及系统运维")

    def test_classify_medical_tcm_mixed_project(self) -> None:
        document = self._document(
            "中药配方颗粒项目.docx",
            ["中药配方颗粒", "自动化调剂", "发药机", "信息化管理系统", "无缝对接"],
        )
        classification = classify_procurement_catalog(document)

        self.assertEqual(classification.primary_domain_key, "medical_tcm_mixed")
        self.assertTrue(classification.is_mixed_scope)
        self.assertIn("信息化平台及系统运维", classification.secondary_catalog_names)

    def test_classify_furniture_with_information_boundary(self) -> None:
        document = self._document(
            "医院办公类家具项目.docx",
            ["办公类家具", "资产定位", "智能管理系统", "安装调试"],
        )
        classification = classify_procurement_catalog(document)

        self.assertEqual(classification.primary_domain_key, "furniture_goods")
        self.assertTrue(classification_has_catalog_prefix(classification, "A0501"))
        self.assertTrue(classification.is_mixed_scope)
        self.assertIn("家具", classification.primary_catalog_name)

    def test_catalog_drives_strategy_and_analyzer_order(self) -> None:
        document = self._document(
            "基础服务体系平台运营项目.docx",
            ["基础服务体系平台运营", "系统运维", "软件著作权", "驻场服务", "演示答辩"],
        )
        classification = classify_procurement_catalog(document)
        strategy = build_document_strategy_profile([], document=document, classification=classification)
        analyzer_order = build_analyzer_execution_order([], document=document, classification=classification)

        self.assertEqual(strategy.primary_catalog_name, "信息化平台及系统运维")
        self.assertIn("scoring", strategy.preferred_analyzer_groups)
        self.assertIn("commercial", strategy.preferred_analyzer_groups)
        self.assertEqual(analyzer_order[0], "scoring")

    def test_full_catalog_skeleton_exists(self) -> None:
        path = REPO_ROOT / "data" / "procurement-catalog" / "catalogs-full.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertGreaterEqual(payload["entry_count"], 4000)
        entries = {item["catalog_code"]: item for item in payload["entries"]}
        self.assertEqual(entries["A"]["catalog_name"], "货物")
        self.assertEqual(entries["A01010100"]["parent_code"], "A01010000")
        self.assertEqual(entries["C20000000"]["category_type"], "service")

    def test_review_domain_map_exists_and_covers_high_frequency_domains(self) -> None:
        entries = load_review_domain_map()
        self.assertGreaterEqual(len(entries), 10)

        by_domain = {item.review_domain_key: item for item in entries}
        self.assertIn("furniture_goods", by_domain)
        self.assertIn("sports_facility_goods", by_domain)
        self.assertIn("information_system", by_domain)
        self.assertIn("medical_device_goods", by_domain)
        self.assertIn("signage_printing_service", by_domain)

        full_catalog = json.loads(
            (REPO_ROOT / "data" / "procurement-catalog" / "catalogs-full.json").read_text(encoding="utf-8")
        )["entries"]
        full_codes = {item["catalog_code"] for item in full_catalog}

        for entry in entries:
            for code in entry.mapped_catalog_codes:
                self.assertIn(code, full_codes)
            for prefix in entry.mapped_catalog_prefixes:
                self.assertTrue(any(code.startswith(prefix) for code in full_codes), prefix)

        self.assertIn("C21040000", by_domain["property_service"].mapped_catalog_codes)
        self.assertIn("A0246", by_domain["sports_facility_goods"].mapped_catalog_prefixes)
        self.assertIn("C1602", by_domain["information_system"].mapped_catalog_prefixes)
        self.assertIn("C2309", by_domain["signage_printing_service"].mapped_catalog_prefixes)

    def test_full_catalog_names_are_resolved_for_review_domains(self) -> None:
        mapping = full_catalog_names_by_code_or_prefix()
        self.assertIn("家具", mapping["CAT-FURNITURE"])
        self.assertIn("体育设备设施", mapping["CAT-SPORTS"])
        self.assertIn("物业管理服务", mapping["CAT-PROPERTY"])
        self.assertIn("信息系统集成实施服务", mapping["CAT-INFO"])
