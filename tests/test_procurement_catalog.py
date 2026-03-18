from __future__ import annotations

import unittest

from agent_compliance.knowledge.procurement_catalog import classify_procurement_catalog, load_procurement_catalogs
from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.schemas import NormalizedDocument


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
        self.assertGreaterEqual(len(catalogs), 8)
        self.assertTrue(any(item.domain_key == "information_system" for item in catalogs))

    def test_classify_information_system_project(self) -> None:
        document = self._document(
            "民生诉求服务平台（二期）项目.docx",
            ["平台建设", "系统对接", "软件著作权", "驻场运维"],
        )
        classification = classify_procurement_catalog(document)

        self.assertEqual(classification.primary_domain_key, "information_system")
        self.assertEqual(classification.primary_catalog_name, "信息化平台及系统运维")
        self.assertFalse(classification.is_mixed_scope)

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
        self.assertTrue(classification.is_mixed_scope)
        self.assertIn("家具", classification.primary_catalog_name)

