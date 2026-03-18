from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.knowledge.references_index import load_reference_records


class ReferencesIndexTest(unittest.TestCase):
    def test_legal_authority_records_include_local_normalized_text_when_available(self) -> None:
        records = load_reference_records()
        legal_001 = next((item for item in records if item.reference_id == "LEGAL-001"), None)
        self.assertIsNotNone(legal_001)
        assert legal_001 is not None
        self.assertEqual(legal_001.content_source, "normalized_authority_text")
        self.assertIn("离线标准化法规文本", legal_001.content)
        self.assertIn("本文件为 `LEGAL-001` 的标准化文本入口样板", legal_001.content)


if __name__ == "__main__":
    unittest.main()
