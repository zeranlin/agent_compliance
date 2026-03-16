from __future__ import annotations

import unittest

from tests._bootstrap import REPO_ROOT
from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.pipelines.review import build_review_result
from agent_compliance.pipelines.rule_scan import run_rule_scan
from agent_compliance.schemas import NormalizedDocument


class ReviewPipelineTest(unittest.TestCase):
    def test_review_result_uses_local_references_and_dedupes_hits(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "投标单位须为外商投资及民营企业，国资企业不具备投标资格。",
                "评标信息",
                "方案极合理、条理极清晰、可操作性极强的得 40 分；",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="abc123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertGreaterEqual(len(review.findings), 2)
        self.assertTrue(any(finding.legal_or_policy_basis for finding in review.findings))
        self.assertIn("本地离线审查共形成", review.overall_risk_summary)


if __name__ == "__main__":
    unittest.main()
