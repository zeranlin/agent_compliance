from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.core.knowledge.legal_clause_index import find_legal_clauses, load_legal_clause_records


class LegalClauseIndexTest(unittest.TestCase):
    def test_clause_index_loads_first_batch_of_legal_authorities(self) -> None:
        records = load_legal_clause_records()
        self.assertGreaterEqual(len(records), 20)
        legal_001 = [item for item in records if item.reference_id == "LEGAL-001"]
        legal_002 = [item for item in records if item.reference_id == "LEGAL-002"]
        self.assertGreaterEqual(len(legal_001), 20)
        self.assertGreaterEqual(len(legal_002), 5)

    def test_find_legal_clauses_supports_reference_and_keyword(self) -> None:
        records = find_legal_clauses(reference_id="LEGAL-001", keyword="资格条件", limit=5)
        self.assertTrue(records)
        self.assertTrue(any("资格条件" in item.clause_text for item in records))
        self.assertTrue(all(item.reference_id == "LEGAL-001" for item in records))


if __name__ == "__main__":
    unittest.main()
