from __future__ import annotations

import unittest

from tests._bootstrap import REPO_ROOT
from agent_compliance.parsers.pagination import build_page_map, page_hint_for_line
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
        self.assertTrue(any(finding.section_path for finding in review.findings))

    def test_splitter_builds_hierarchical_section_path_and_table_label(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "评标信息",
                "技术部分",
                "评分因素",
                "方案极合理、条理极清晰、可操作性极强的得 40 分；",
            ]
        )
        clauses = split_into_clauses(text)
        target = clauses[-1]
        self.assertEqual(target.section_path, "第一章 招标公告-评标信息-技术部分-评分因素")
        self.assertEqual(target.table_or_item_label, "评分因素")

    def test_page_map_assigns_estimated_page_hint(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "投标单位须为外商投资及民营企业，国资企业不具备投标资格。",
                "评标信息",
                "评分因素",
            ]
        )
        page_map = build_page_map(text, lines_per_page=2)
        clauses = split_into_clauses(text, page_map=page_map)

        self.assertEqual(page_hint_for_line(3, page_map), "第2页（估算）")
        self.assertEqual(clauses[2].page_hint, "第2页（估算）")

    def test_generic_table_headers_do_not_pollute_section_path(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "评标信息",
                "序号",
                "内容",
                "评分项",
                "技术部分",
                "序号",
                "评分因素",
                "评分准则",
                "方案极合理、条理极清晰、可操作性极强的得 40 分；",
            ]
        )
        clauses = split_into_clauses(text)
        target = clauses[-1]

        self.assertEqual(target.section_path, "第一章 招标公告-评标信息-评分项-技术部分-评分因素")
        self.assertEqual(target.table_or_item_label, "评分因素")

    def test_review_groups_adjacent_same_issue_hits(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "评标信息",
                "技术部分",
                "评分因素",
                "若供应商提供守合同重信用企业，可得10分。",
                "若供应商提供全国科技型中小企业证明，可得10分。",
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

        self.assertEqual(len(review.findings), 1)
        self.assertEqual(review.findings[0].text_line_start, 5)
        self.assertEqual(review.findings[0].text_line_end, 6)
        self.assertIn("守合同重信用企业", review.findings[0].source_text)
        self.assertIn("科技型中小企业", review.findings[0].source_text)
        self.assertIn("同一评分项已合并", review.findings[0].problem_title)
        self.assertIn("统一改写", review.findings[0].rewrite_suggestion)

    def test_review_drops_appendix_duplicate_findings(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "一、电子图像处理器",
                "17.具备无线插拔技术、无线连接技术。",
                "第四章 投标文件组成要求及格式",
                "一、电子图像处理器",
                "17.具备无线插拔技术、无线连接技术。",
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

        self.assertEqual(len(review.findings), 1)
        self.assertIn("第三章 用户需求书", review.findings[0].section_path)
        self.assertNotIn("第四章 投标文件组成要求及格式", review.findings[0].section_path)

    def test_review_merges_same_technical_family_across_sections(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "三、电子上消化道内窥镜",
                "10.具备无线插拔技术、无线连接技术，内镜无需防水盖，可直接浸泡消毒。",
                "四、电子下消化道内窥镜",
                "10.具备无线插拔技术、无线连接技术，内镜无需防水盖，可直接浸泡消毒。",
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

        self.assertEqual(len(review.findings), 1)
        self.assertIn("多个设备章节", review.findings[0].problem_title)
        self.assertIn("电子上消化道内窥镜 / 四、电子下消化道内窥镜", review.findings[0].section_path)

    def test_review_uses_representative_excerpt_for_long_source_text(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "10.供应商注册资本不低于100万元。同时，供应商年收入不低于50万元，净利润不低于20万元。",
                "该企业的股权结构由国有资本持股51%以确保控股地位。经营年限不低于10年。",
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

        self.assertEqual(len(review.findings), 2)
        self.assertTrue(any("股权结构" in finding.source_text for finding in review.findings))
        self.assertTrue(any(len(finding.source_text) < 90 for finding in review.findings))

    def test_review_splits_distinct_qualification_barriers(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "供应商须提供其上级主管单位（须为省部级机关单位）出具的同意其参与投标的函件。",
                "该企业的股权结构由国有资本持股41%以确保控股地位。",
                "投标人必须提供自2020年至2024年（含）连续五个会计年度的、由注册会计师事务所出具的财务审计报告。",
                "投标人必须是经认定的国家级特色企业。",
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

        self.assertEqual(len(review.findings), 4)
        self.assertTrue(any("主管单位" in finding.source_text for finding in review.findings))
        self.assertTrue(any("股权结构" in finding.source_text for finding in review.findings))
        self.assertTrue(any("财务审计报告" in finding.source_text for finding in review.findings))
        self.assertTrue(any("国家级特色企业" in finding.source_text for finding in review.findings))

    def test_review_flags_scoring_weight_and_post_award_proof(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "认证证书",
                "投标人通过质量管理体系认证得33分；投标人通过职业健康安全管理体系认证得33分；投标人通过环境管理体系认证得34分。",
                "注：如投标人距本项目开标之日的注册成立时间不足3个月，可承诺中标（成交）后4个月内取得评审因素相关认证证书。",
                "供应商同类业绩",
                "投标人自2021年1月1日至本项目投标截止承接过窗帘采购项目业绩的，每提供1个得20分，最高得100分。",
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

        issue_types = {finding.issue_type for finding in review.findings}
        self.assertIn("excessive_scoring_weight", issue_types)
        self.assertIn("post_award_proof_substitution", issue_types)
        self.assertTrue(any("中标后补证" in finding.problem_title or "补证" in finding.problem_title for finding in review.findings))

    def test_review_flags_sample_scoring_weight_and_commercial_risk_shift(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "样品",
                "（1）材质好，质量好，做工优秀，完全满足采购单位需求，评审为优加 80 分；",
                "第三章 用户需求书",
                "商务要求",
                "★2.5 中标后，实际供货均需满足投标文件及国家标准要求，否则采购人有权拒绝收货，相关损失及责任均与采购人无关。",
                "3.3 中标人负责安装、调试。安装调试中发生的一切事故，相关责任全部由供应商承担，采购人对此不承担任何责任。",
                "★4.1 采购方有权实施抽样检测。出现抽样或检测不合格的，中标人需承担检测费、抽样人工费、差旅费及相关费用。",
                "（3）终验款：货物通过有关部门抽检终验后，采购人支付合同总金额30%的货款。",
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

        issue_types = {finding.issue_type for finding in review.findings}
        self.assertIn("excessive_scoring_weight", issue_types)
        self.assertIn("one_sided_commercial_term", issue_types)
        self.assertIn("payment_acceptance_linkage", issue_types)


if __name__ == "__main__":
    unittest.main()
