from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.core.knowledge.issue_type_authority_map import (
    get_issue_type_authority_record,
    load_issue_type_authority_records,
)


class IssueTypeAuthorityMapTest(unittest.TestCase):
    def test_loads_first_batch_of_high_frequency_issue_types(self) -> None:
        records = load_issue_type_authority_records()
        issue_types = {item.issue_type for item in records}
        self.assertIn("excessive_supplier_qualification", issue_types)
        self.assertIn("qualification_domain_mismatch", issue_types)
        self.assertIn("geographic_restriction", issue_types)
        self.assertIn("scoring_content_mismatch", issue_types)
        self.assertIn("ambiguous_requirement", issue_types)
        self.assertIn("one_sided_commercial_term", issue_types)
        self.assertIn("unclear_acceptance_standard", issue_types)
        self.assertIn("technical_justification_needed", issue_types)

    def test_single_issue_type_returns_primary_clause_mapping(self) -> None:
        record = get_issue_type_authority_record("scoring_content_mismatch")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertIn("LEGAL-001-ART-021", record.primary_clause_ids)
        self.assertTrue(record.reasoning_template)
        self.assertIn("评分", "".join(record.fallback_review_topics))


if __name__ == "__main__":
    unittest.main()
