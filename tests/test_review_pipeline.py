from __future__ import annotations

import unittest

from tests._bootstrap import REPO_ROOT
from agent_compliance.knowledge.procurement_catalog import classify_procurement_catalog
from agent_compliance.parsers.pagination import build_page_map, page_hint_for_line
from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.pipelines.review_evidence import select_representative_evidence
from agent_compliance.pipelines.review import _drop_false_positive_findings, build_review_result
from agent_compliance.pipelines.rule_scan import run_rule_scan
from agent_compliance.schemas import Finding, NormalizedDocument


class ReviewPipelineTest(unittest.TestCase):
    def test_review_summary_prefers_sports_facility_catalog(self) -> None:
        text = "\n".join(
            [
                "项目名称：2025年省级全民健身工程（多功能运动场项目）",
                "运动场围网及照明系统",
                "硅PU面层",
                "体育比赛用灯",
                "二维码报修",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sports.docx",
            document_name="2025年省级全民健身工程（多功能运动场项目）.docx",
            file_hash="sports123",
            normalized_text_path="/tmp/sports.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertIn("当前主品目识别为体育器材及运动场设施", review.overall_risk_summary)

    def test_sports_scoring_theme_is_raised_for_technical_weight_and_test_bonus(self) -> None:
        text = "\n".join(
            [
                "项目名称：2025年省级全民健身工程（多功能运动场项目）",
                "评标信息",
                "技术部分满分78分。",
                "价格部分满分10分。",
                "每一项负偏离扣2分，扣完为止。",
                "提供CMA或CNAS检测报告的，每提供1项得2分。",
                "围网、硅PU面层和体育比赛用灯等运动场设施应满足采购需求。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sports-score.docx",
            document_name="2025年省级全民健身工程（多功能运动场项目）.docx",
            file_hash="sports-score",
            normalized_text_path="/tmp/sports-score.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertTrue(
            any(
                finding.problem_title == "技术评分权重过高且负偏离、专项检测加分进一步放大结构失衡"
                for finding in review.findings
            )
        )

    def test_review_adds_sports_mixed_scope_theme_for_lightweight_smart_features(self) -> None:
        text = "\n".join(
            [
                "项目名称：2025年省级全民健身工程（多功能运动场项目）",
                "多功能运动场",
                "围网、硅PU面层和体育比赛用灯等运动场设施应满足采购需求。",
                "提供二维码报修系统，支持OTA远程升级。",
                "支持智能显示联动。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sports-mixed.docx",
            document_name="2025年省级全民健身工程（多功能运动场项目）.docx",
            file_hash="sports-mixed",
            normalized_text_path="/tmp/sports-mixed.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertTrue(
            any(
                finding.problem_title == "体育器材及运动场设施叠加轻量智能化功能，边界需进一步论证"
                for finding in review.findings
            )
        )

    def test_review_requires_core_delivery_clues_for_sports_mixed_scope_theme(self) -> None:
        text = "\n".join(
            [
                "项目名称：2025年省级全民健身工程（多功能运动场项目）",
                "运动场围网及照明系统",
                "提供二维码报修系统。",
                "围网、硅PU面层和体育比赛用灯等运动场设施应满足采购需求。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sports-mixed-no-core.docx",
            document_name="2025年省级全民健身工程（多功能运动场项目）.docx",
            file_hash="sports-mixed-no-core",
            normalized_text_path="/tmp/sports-mixed-no-core.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertFalse(
            any(
                finding.problem_title == "体育器材及运动场设施叠加轻量智能化功能，边界需进一步论证"
                for finding in review.findings
            )
        )

    def test_review_requires_more_than_two_lightweight_sports_support_markers_without_hard_mismatch(self) -> None:
        text = "\n".join(
            [
                "项目名称：2025年省级全民健身工程（多功能运动场项目）",
                "围网、硅PU面层和体育比赛用灯等运动场设施应满足采购需求。",
                "支持二维码报修系统。",
                "支持智能显示联动。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sports-mixed-lightweight.docx",
            document_name="2025年省级全民健身工程（多功能运动场项目）.docx",
            file_hash="sports-mixed-lightweight",
            normalized_text_path="/tmp/sports-mixed-lightweight.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertFalse(
            any(
                finding.problem_title == "体育器材及运动场设施叠加轻量智能化功能，边界需进一步论证"
                for finding in review.findings
            )
        )

    def test_review_ignores_hint_and_format_text_for_medical_mixed_scope_theme(self) -> None:
        text = "\n".join(
            [
                "项目名称：[BACG2025000096-A]深圳市宝安区中心医院胃肠镜类设备采购项目",
                "第三章 用户需求书",
                "本项目为胃肠镜类设备采购，供应商负责设备供货、安装、调试和验收。",
                "提供开机培训和售后保修服务。",
                "第四章 投标文件组成要求及格式",
                "特别警示条款：投标文件制作工具会记录文件创建标识码。",
                "深圳政府采购智慧平台提示：如有方案表述中有出现类似可实现、实现、可支持、支持等描述，均应提供佐证。",
                "政府采购投标及履约承诺函",
                "供应商承诺免费开放软件端口、完成医院信息系统对接并提交碳足迹盘查报告。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/medical-scope-filter.docx",
            document_name="[BACG2025000096-A]深圳市宝安区中心医院胃肠镜类设备采购项目.docx",
            file_hash="medical-scope-filter",
            normalized_text_path="/tmp/medical-scope-filter.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertFalse(
            any(
                finding.problem_title == "设备采购场景叠加信息化接口和碳足迹义务，边界不清"
                for finding in review.findings
            )
        )

    def test_review_prefers_hard_mismatch_over_equipment_only_in_signage_scope(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院导视标识和宣传印刷服务",
                "设计制作与现场安装维护应满足采购需求。",
                "投标人具备UV打印机、喷绘机、写真机的得10分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage-mixed-light.docx",
            document_name="医院导视标识和宣传印刷服务.docx",
            file_hash="signage-mixed-light",
            normalized_text_path="/tmp/signage-mixed-light.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertFalse(
            any(
                finding.problem_title == "标识标牌及宣传印制服务叠加设备保障和信息化支撑内容，边界不清"
                for finding in review.findings
            )
        )

    def test_representative_evidence_prefers_catalog_relevant_keywords(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院导视标识和宣传印刷服务",
                "评标信息",
                "投标人具有软件著作权登记证书得10分。",
                "投标人具有UV打印机、喷绘机、写真机的得10分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage.docx",
            document_name="医院导视标识和宣传印刷服务.docx",
            file_hash="signage-evidence",
            normalized_text_path="/tmp/signage.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        classification = classify_procurement_catalog(document)
        finding = Finding(
            finding_id="F-001",
            document_name=document.document_name,
            problem_title="评分项名称、内容和评分证据之间不一致",
            page_hint=None,
            clause_id=clauses[2].clause_id,
            source_section=clauses[2].source_section or "",
            section_path=clauses[2].section_path,
            table_or_item_label=clauses[2].table_or_item_label,
            text_line_start=clauses[2].line_start,
            text_line_end=clauses[3].line_end,
            source_text="；".join([clauses[2].text, clauses[3].text]),
            issue_type="scoring_content_mismatch",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis=None,
            rewrite_suggestion="x",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
        excerpt = select_representative_evidence(finding, classification=classification)
        self.assertIn("软件著作权", excerpt)

    def test_representative_evidence_filters_out_hint_text(self) -> None:
        finding = Finding(
            finding_id="F-001",
            document_name="test.docx",
            problem_title="设备采购场景叠加信息化接口和碳足迹义务，边界不清",
            page_hint=None,
            clause_id="c-1",
            source_section="第三章 用户需求书",
            section_path="第三章 用户需求书-用户需求书",
            table_or_item_label=None,
            text_line_start=1,
            text_line_end=9,
            source_text="本项目为胃肠镜类设备采购，供应商负责设备供货、安装、调试和验收。；特别警示条款：投标文件制作工具会记录文件创建标识码。",
            issue_type="template_mismatch",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky="x",
            impact_on_competition_or_performance="x",
            legal_or_policy_basis=None,
            rewrite_suggestion="x",
            needs_human_review=True,
            human_review_reason="x",
            finding_origin="analyzer",
        )
        excerpt = select_representative_evidence(finding)
        self.assertIn("设备供货、安装、调试和验收", excerpt)
        self.assertNotIn("文件创建标识码", excerpt)

    def test_scoring_semantic_consistency_uses_catalog_profile_markers(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院导视标识和宣传印刷服务",
                "评标信息",
                "评分项一：投标人具有IT服务管理体系认证得20分。",
                "评分项二：投标人具有保安服务认证得20分。",
                "评分项三：投标人具有软件著作权登记证书得20分。",
                "评分项四：投标人承诺系统端口无缝对接得20分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage-score-semantic.docx",
            document_name="医院导视标识和宣传印刷服务.docx",
            file_hash="signage-score-semantic",
            normalized_text_path="/tmp/signage-score-semantic.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        target = next(
            (finding for finding in review.findings if finding.problem_title == "评分项名称、内容和评分证据之间不一致"),
            None,
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertIn("核心履约能力", target.why_it_is_risky)
        self.assertIn("核心交付、实施组织和履约保障能力", target.rewrite_suggestion)

    def test_scoring_semantic_consistency_uses_theme_and_evidence_profiles(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院导视标识和宣传印刷服务",
                "评标信息",
                "评分项一：投标人具有软件著作权登记证书得20分。",
                "评分项二：投标人具有IT服务管理体系认证得20分。",
                "评分项三：投标人承诺系统端口无缝对接得20分。",
                "评分项四：投标人具备设计方案和打样方案的得5分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage-theme-evidence.docx",
            document_name="医院导视标识和宣传印刷服务.docx",
            file_hash="signage-theme-evidence",
            normalized_text_path="/tmp/signage-theme-evidence.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        target = next(
            (finding for finding in review.findings if finding.problem_title == "评分项名称、内容和评分证据之间不一致"),
            None,
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertIn("评分更适合围绕设计制作", target.why_it_is_risky)
        self.assertIn("优先采用设计方案", target.rewrite_suggestion)

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
        self.assertTrue(any(finding.primary_authority for finding in review.findings))
        self.assertTrue(any(finding.applicability_logic for finding in review.findings))
        self.assertIn("本地离线审查共形成", review.overall_risk_summary)
        self.assertTrue(any(finding.section_path for finding in review.findings))

    def test_review_summary_includes_catalog_strategy(self) -> None:
        text = "\n".join(
            [
                "项目名称：中药配方颗粒项目",
                "设备需求参数",
                "自动化调剂设备",
                "系统端口无缝对接",
                "信息化管理系统",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/tcm.docx",
            document_name="中药配方颗粒项目.docx",
            file_hash="tcm123",
            normalized_text_path="/tmp/tcm.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        hits = run_rule_scan(document)
        review = build_review_result(document, hits)

        self.assertIn("当前主品目识别为药品及医用配套", review.overall_risk_summary)
        self.assertIn("当前识别为混合采购场景", review.overall_risk_summary)

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

        self.assertGreaterEqual(len(review.findings), 1)
        merged_source = " ".join(finding.source_text for finding in review.findings if finding.source_text)
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("主管单位", merged_source)
        self.assertIn("股权结构", merged_source)
        self.assertIn("国家级特色企业", merged_source)
        self.assertIn("资格条件整体超出法定准入和履约必需范围", titles)

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

    def test_review_flags_qualification_domain_mismatch_and_general_thresholds(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "投标人须有A级有害生物防制（治）服务企业资质证书。",
                "投标人须具备SPCA登记证书。",
                "投标人须提供近三年年均纳税额不低于50万元的完税证明。",
                "投标人须具备连续3年以上经营业绩证明。",
                "投标人须具备单项合同金额不低于100万元的柴油发电机组供货业绩。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="qualx123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        issue_types = {finding.issue_type for finding in review.findings}
        self.assertIn("qualification_domain_mismatch", issue_types)
        self.assertIn("excessive_supplier_qualification", issue_types)

    def test_review_adds_qualification_bundle_theme_finding(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "供应商2024年度的纳税总额不得低于人民币500万元。",
                "营业执照的成立日期不得晚于2020年1月1日。",
                "供应商必须在高新区内拥有固定的售后服务场所。",
                "供应商在册员工总数不得少于100人。",
                "供应商最近三个会计年度的年末平均资产总额不低于4000万元人民币。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="qual-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件设置一般财务和规模门槛", titles)
        self.assertIn("资格条件设置经营年限、属地场所或单项业绩门槛", titles)

    def test_review_adds_brand_and_certification_scoring_themes(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "商务部分",
                "选用格力、美的、海尔等国内一线品牌或大金、日立等国际知名品牌，得3分；选用其他国产品牌得1分。",
                "供应商认证情况",
                "投标人作为全国科技型中小企业。",
                "投标人具有高空清洗悬吊作业企业安全生产证书。",
                "投标人具有CCRC信息安全服务资质认证证书。",
                "投标人具备ISO20000体系认证。",
                "投标人具备商品售后服务评价体系认证证书。",
                "投标人获得中国驰名商标称号。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="brand-cert-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("评分项直接按品牌档次赋分", titles)
        self.assertIn("认证评分混入错位证书且高分值结构失衡", titles)

    def test_review_adds_scoring_semantic_and_personnel_themes(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "拟安排项目负责人情况",
                "项目负责人具有博士学位得3分，具有高级工程师职称证书得3分，获得省部级奖项得3分。",
                "拟安排的项目团队成员情况",
                "团队成员具有PMP证书、人工智能应用工程师证书、大数据应用工程师证书和特种设备安全管理和作业人员证书的得分。",
                "技术方案",
                "项目实施方案中提供工程案例和具有CMA标识的检测报告得分。",
                "商务情况",
                "营业收入、净利润、资产总额和成立时间分别得分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="score-semantic",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("人员与团队评分混入错位证书并过度堆叠条件", titles)
        self.assertTrue(
            "评分项名称、内容和评分证据之间不一致" in titles
            or "评分内容与评分主题或采购标的不完全匹配（同一评分项已合并）" in titles
        )

    def test_review_adds_demo_theme_for_official_information_catalog_name(self) -> None:
        text = "\n".join(
            [
                "项目名称：信息系统集成实施服务项目",
                "评标信息",
                "演示答辩",
                "投标人提供可运行展示系统的得40分，仅提供系统原型、PPT或视频的得10分。",
                "投标人须在开标后60分钟内完成现场演示签到，迟到或缺席的，演示及答辩相关评分项得0分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/official-info-catalog.txt",
            document_name="信息系统集成实施服务项目.docx",
            file_hash="official-info-catalog",
            normalized_text_path="/tmp/official-info-catalog.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("现场演示分值过高且签到要求形成额外门槛", titles)

    def test_review_adds_service_scoring_signal_and_warranty_weight_theme(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "售后服务方案",
                "投标人具有深圳市政府部门颁发的先进单位荣誉证书得30分。",
                "人员至少具有1位注册安全工程师证书。",
                "方案极合理、条理极清晰、可操作性极强的得70分。",
                "免费质保期",
                "在满足招标文件《商务要求》免费质保期要求的前提下，整体每延长1年免费质保期的得100分，最高100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="service-warranty-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("免费质保期延长按年度直接高分赋值", titles)

    def test_review_adds_commercial_lifecycle_theme(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "商务要求",
                "验收合格后支付合同价款。",
                "所有送检、检测和专家评审费用由供应商承担。",
                "24小时内到场处理问题，否则采购人有权另行委托。",
                "项目验收后履约保证金自动转为售后服务保证金，质保期结束后退还。",
                "采购人可根据实际需求调整服务范围，中标人应无条件配合。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="commercial-life",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担", titles)

    def test_review_adds_technical_themes_for_official_signage_catalog_name(self) -> None:
        text = "\n".join(
            [
                "项目名称：印刷服务项目",
                "技术要求",
                "需提供交通部交工验收认可的试验成果，并提交工程现场勘察记录。",
                "投标人应提供经广告审查机关备案的产品彩页及本市具有检验检测机构出具的检测报告原件扫描件。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/official-signage-catalog.txt",
            document_name="印刷服务项目.docx",
            file_hash="official-signage-catalog",
            normalized_text_path="/tmp/official-signage-catalog.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("技术要求引用了与标的不匹配的标准或规范", titles)
        self.assertIn("技术证明材料形式要求过严且带有地方化限制", titles)

    def test_review_adds_property_personnel_theme_for_official_catalog_name(self) -> None:
        text = "\n".join(
            [
                "项目名称：物业管理服务项目",
                "评标信息",
                "拟安排项目负责人情况",
                "项目负责人具有本科及以上学历、医院物业管理项目经验和特种设备安全管理和作业人员证书的得分。",
                "拟安排的项目团队成员情况",
                "团队成员具有保洁管理经验、保安管理经验和医院评审项目经验的得分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/official-property-catalog.txt",
            document_name="物业管理服务项目.docx",
            file_hash="official-property-catalog",
            normalized_text_path="/tmp/official-property-catalog.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("人员与团队评分混入错位证书并过度堆叠条件", titles)

    def test_review_commercial_lifecycle_covers_uptime_backup_and_payment_relief(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "商务要求",
                "在免费保修期内，中标人应在2小时内响应，12小时内到达现场维修，并在48小时内消除故障；不能及时排除故障的，应在2个日历天内免费提供备用设备。",
                "免费保修期内，中标人应确保设备年开机率在95%以上，否则应延长维保期、更换新设备并赔偿直接经济损失和间接经济损失。",
                "因财政审批的原因造成采购人延期付款的，采购人不承担违约责任。",
                "采购人可以视具体情况暂时中止支付争议款项或其他相关款项。",
                "如采购人需要，中标人需无条件配合委托第三方质量检测并承担相应后果。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="commercial-uptime-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担", titles)

    def test_review_adds_commercial_themes_for_official_medical_device_catalog_name(self) -> None:
        text = "\n".join(
            [
                "项目名称：医疗设备项目",
                "商务要求",
                "项目验收后履约保证金自动转为售后服务保证金，质保期结束后退还。",
                "免费保修期内中标人应确保设备年开机率在95%以上，不能及时排除故障的应提供备用设备。",
                "采购人可以视具体情况暂时中止支付争议款项，必要时委托第三方质量检测。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/official-medical-device-catalog.txt",
            document_name="医疗设备项目.docx",
            file_hash="official-medical-device-catalog",
            normalized_text_path="/tmp/official-medical-device-catalog.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("商务条款设置异常资金占用安排", titles)
        self.assertIn("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担", titles)

    def test_arbiter_drops_overbroad_commercial_lifecycle_when_specific_themes_are_present(self) -> None:
        text = "\n".join(
            [
                "项目名称：物业管理服务项目",
                "商务要求",
                "每月服务费与履约评价结果挂钩，管理费直接挂钩，满意度评价结果与服务费挂钩，支付对应阶段款。",
                "项目负责人可根据项目要求自行设定评价标准、评价指标和分值。",
                "履约评价不合格的，对应阶段款不予支付。",
                "所有送检、检测、专家评审和复检费用均由供应商承担。",
                "如出现违约情形，采购人可解除合同并从应付货款中直接扣除违约金。",
                "供应商应24小时内到场处理，否则采购人可另行委托。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/property-commercial-specifics.docx",
            document_name="物业管理服务项目.docx",
            file_hash="property-commercial-specifics",
            normalized_text_path="/tmp/property-commercial-specifics.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("付款条件与履约评价结果深度绑定且评价标准开放", titles)
        self.assertIn("验收送检、检测和专家评审费用整体转嫁给供应商", titles)
        self.assertIn("商务责任和违约后果设置明显偏重", titles)
        self.assertNotIn("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担", titles)

    def test_review_adds_property_service_penalty_chain_theme_and_drops_overbroad_lifecycle(self) -> None:
        text = "\n".join(
            [
                "项目名称：物业管理服务项目",
                "商务要求",
                "每月服务费与考核结果挂钩，管理费直接挂钩，满意度评价结果与服务费挂钩。",
                "月得分每低1分，按1%扣减当月物业服务费。",
                "采购人可及时修正《标准》，供应商应无条件服从。",
                "连续两次被评级为“中”或考核不合格的，甲方有权解除合同。",
                "供应商应24小时内到场处理。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/property-penalty-theme.docx",
            document_name="物业管理服务项目.docx",
            file_hash="property-penalty-theme",
            normalized_text_path="/tmp/property-penalty-theme.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("考核扣罚、满意度评价与解除合同后果叠加偏重", titles)
        self.assertNotIn("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担", titles)

    def test_review_overall_summary_includes_document_strategy_route(self) -> None:
        text = "\n".join(
            [
                "项目名称：北京大学深圳医院中药配方颗粒项目",
                "申请人的资格要求",
                "供应商成立日期必须早于2022年1月1日。",
                "供应商最近三个会计年度的年均纳税总额不低于300万元人民币。",
                "用户需求书",
                "投标人承诺提供与采购人业务规模相适应的信息化管理系统，并开发系统端口与医院综合业务协同平台无缝对接。",
                "履约担保",
                "以现金形式缴纳采购预算的5%作为履约保证金。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="北京大学深圳医院中药配方颗粒项目.docx",
            file_hash="strategy-route",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("文件级风险画像", review.overall_risk_summary)

    def test_review_splits_qualification_bundle_themes(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "供应商2024年度的纳税总额不得低于人民币500万元。",
                "供应商在册员工总数不得少于100人。",
                "供应商最近三个会计年度的年末平均资产总额不低于4000万元人民币。",
                "营业执照的成立日期不得晚于2020年1月1日。",
                "供应商必须在高新区内拥有固定的售后服务场所。",
                "供应商须具备单项合同金额不低于100万元的同类业绩。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="qual-split-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件整体超出法定准入和履约必需范围", titles)
        self.assertIn("资格条件设置一般财务和规模门槛", titles)
        self.assertIn("资格条件设置经营年限、属地场所或单项业绩门槛", titles)

    def test_review_splits_technical_reference_consistency_themes(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "四、技术要求",
                "1.2 实时采样率≥2GSa/S；并提供2022年起至投标截止之日期间，本市具有检验检测机构出具的带有CMA认证标志的检测报告。",
                "1.4 垂直档位500uV/div -10V/div，需符合QB/T 8101-2024《家用和类似用途电器空气质量检测装置》标准要求。",
                "1.18 提供省级或以上权威质检部门出具的带有CMA标识的检测报告原件扫描件。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="tech-ref-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("技术要求引用了与标的不匹配的标准或规范", titles)
        self.assertIn("技术证明材料形式要求过严且带有地方化限制", titles)

    def test_review_splits_commercial_burden_themes(self) -> None:
        text = "\n".join(
            [
                "第二章 对通用条款的补充内容及其他关键信息",
                "履约担保",
                "缴纳预算金额的5%作为履约担保。",
                "缴纳2%作为诚信履约备用金。",
                "项目验收后履约保证金自动转为售后服务保证金，质保期满后无息退还。",
                "第三章 用户需求书",
                "交货期限",
                "★合同签订后1000个日历日内交货。",
                "安装、调试、验收及相关技术文件、资料",
                "所有与验收环节相关的报验、送检、检测报告出具及专家评审等费用，均应计入投标单价，由供应商自行消化。",
                "空气检测费用、监理费用和复验费用均由供应商承担。",
                "违约责任",
                "中标人应赔偿采购人因此遭受的一切损失；采购人可主张中标人向采购人支付不超过合同总价百分之三十的违约金。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="commercial-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("商务条款设置异常资金占用安排", titles)
        self.assertIn("交货期限设置异常或明显失真", titles)
        self.assertIn("验收送检、检测和专家评审费用整体转嫁给供应商", titles)
        self.assertIn("商务责任和违约后果设置明显偏重", titles)

    def test_review_adds_geographic_tendency_theme(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "售后服务要求",
                "供应商须在高新区内设有固定的售后服务场所。",
                "接到故障通知后1小时内到达现场并提供驻场服务。",
                "供应商须设有驻点服务站，并在12小时内提供备件。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="geo-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("驻场、短时响应或服务场地要求形成事实上的属地倾斜", titles)

    def test_review_adds_acceptance_and_industry_theme_findings(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "技术要求",
                "需符合QB/T 8101-2024《家用和类似用途电器空气质量检测装置》标准。",
                "验收要求",
                "所有与验收环节相关的报验、送检、检测报告出具及专家评审等费用，均由供应商自行消化。",
                "技术验收、商务验收、复检及最终验收结果均以采购人验收报告为准。",
                "评分项",
                "投标人具有CCRC信息安全服务资质认证证书。",
                "投标人具有ISO20000体系认证。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="accept-industry-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("验收程序、复检与最终确认边界不清", titles)
        self.assertIn("评分和技术要求中存在行业适配性不足的错位内容", titles)

    def test_theme_splitter_summarizes_theme_excerpt(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "供应商认证情况",
                "投标人作为全国科技型中小企业。",
                "投标人具有高空清洗悬吊作业企业安全生产证书。",
                "投标人具有CCRC信息安全服务资质认证证书。",
                "投标人具备ISO20000体系认证。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="theme-excerpt",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        target = next(
            finding for finding in review.findings if finding.problem_title == "认证评分混入错位证书且高分值结构失衡"
        )
        self.assertIn("等", target.source_text)
        self.assertIn("高权重", target.why_it_is_risky)

    def test_finding_arbiter_prefers_theme_findings_over_scoring_fragments(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "技术服务方案",
                "方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。",
                "实施方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。",
                "培训方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。",
                "演示要求",
                "可运行展示系统完整演示得 25 分，原型或PPT演示得 10 分。",
                "开标后 60 分钟内签到，迟到或缺席的演示评分项得 0 分。",
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

        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("多个方案评分项大量使用主观分档且缺少量化锚点", titles)

    def test_subjective_scoring_theme_can_merge_two_high_weight_items(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "售后服务方案",
                "①方案极合理、条理极清晰、可操作性极强的得 70 分；②方案合理、条理清晰、可操作强的得 40分；③方案较合理、条理较清晰、可操作较强的得 10 分。",
                "培训服务方案",
                "①方案极合理、条理极清晰、可操作性极强的得 70 分；②方案合理、条理清晰、可操作强的得 40分；③方案较合理、条理较清晰、可操作较强的得 10 分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="subjective-two-high",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("多个方案评分项大量使用主观分档且缺少量化锚点", titles)

    def test_technical_justification_noise_filters_packaging_and_generic_compliance(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "项目采购内容中包含需要对相关产品需要进行商品包装和快递包装的，投标人承诺所进行的商品包装和快递包装满足财政部《商品包装政府采购需求标准（试行）》《快递包装政府采购需求标准（试行）》的要求。",
                "第五章 合同条款",
                "乙方所提供的货物应符合国家有关安全、环保、卫生的规定。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="technical-noise",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("技术要求可能合理但需补充必要性论证", titles)
        self.assertNotIn("安全环保类技术要求可能合理但需补充必要性论证", titles)
        self.assertEqual(titles, set())

    def test_review_flags_scoring_content_mismatch_and_filters_non_scoring_noise(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "施工组织方案及安全保障措施",
                "发电机组安装的工程案例。",
                "投标人须提供具有CMA标识的第三方检测报告。",
                "商务条款偏离情况",
                "投标人从业人员超过100人的，得3分；资产总额达到3000万元以上的，得3分；成立时间满3年的得2分。",
                "供应商认证情况",
                "投标人具备有机产品认证证书。",
                "制造商发电机组资质证书",
                "投标人具备水运机电工程专项监理企业资质认定的，得5分。",
                "第六章 政府采购履约异常情况反馈表",
                "履约情况评价分为优、良、中、差四个等级。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="scorex123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        self.assertTrue(any(finding.issue_type == "scoring_content_mismatch" for finding in review.findings))
        self.assertFalse(any("履约异常情况反馈表" in (finding.section_path or "") for finding in review.findings))

    def test_qualification_theme_ignores_statement_form_text(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "1.具有独立法人资格。",
                "2.本项目不接受联合体投标。",
                "第四章 投标文件组成要求及格式",
                "三、投标人情况及资格证明文件",
                "中小企业声明函填写说明",
                "从业人员、营业收入、资产总额等指标应如实填写。",
                "政府采购投标及履约承诺函",
                "投标人提供社保缴纳证明、学历学位证书等材料。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="qual-filter",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_scoring_semantic_consistency_flags_furniture_software_copyright_mismatch(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "创新能力评价",
                "投标人所投“定位管理标签模块”具有资产管理读写基站相关的软件著作权证书或专利证书得100分。",
                "提供国家版权局或国家知识产权局颁发的计算机软件著作权登记证书扫描件或专利证书扫描件。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/furniture.txt",
            document_name="医院家具采购项目.txt",
            file_hash="furniture-score-semantic",
            normalized_text_path="/tmp/furniture.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("评分项中存在与标的域不匹配的证书认证或模板内容", titles)

    def test_mixed_scope_boundary_flags_furniture_asset_tracking_scope(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "商务要求",
                "中标后所有家具交货后，需安装1套低功耗近场通讯的蓝牙或UWB以上资产定位管理系统。",
                "根据甲方需求在中标所有家具上安装智能芯片，可通过软件管理系统在线实时查询家具资产所在位置和归属信息。",
                "中标人应开展产品碳足迹数据收集及核算工作。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/furniture.txt",
            document_name="办公类家具项目.txt",
            file_hash="furniture-mixed-scope",
            normalized_text_path="/tmp/furniture.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("家具采购场景叠加资产定位和智能管理系统义务，边界不清", titles)

    def test_commercial_lifecycle_theme_stays_in_substantive_commercial_section(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "商务要求",
                "在免费保修期内，一旦发生质量问题，中标人保证在接到通知24小时内赶到现场进行修理或更换。",
                "货物通过有关部门终验后，采购人支付合同总金额20%的货款。",
                "中标单位承担相关费用。如果发现所交货物与投标文件中所承诺的不符，由此发生的一切损失和费用由中标人承担。",
                "第四章 投标文件组成要求及格式",
                "政府采购投标及履约承诺函",
                "投标人提供符合相关要求的承诺函得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/furniture.txt",
            document_name="办公类家具项目.txt",
            file_hash="commercial-focus",
            normalized_text_path="/tmp/furniture.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        lifecycle = next(
            finding
            for finding in review.findings
            if finding.problem_title == "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担"
        )
        self.assertIn("商务要求", lifecycle.section_path or "")
        self.assertNotIn("投标文件组成要求及格式", lifecycle.section_path or "")

    def test_review_flags_fixed_year_and_manufacturer_engineer_and_payment_shift(self) -> None:
        text = "\n".join(
            [
                "技术要求",
                "产品应选用原装产品，生产日期必须是2025年。",
                "该技术人员必须为柴油发电机制造商厂的专业工程师，有指导安装、调试同类设备5年以上工作经验。",
                "商务要求",
                "工程全部安装调试完成经采购人现场验收合格设备正常运行三个月后支付合同总价的20%。",
                "采购人不承担任何责任及相关费用。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="techbiz123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        issue_types = {finding.issue_type for finding in review.findings}
        self.assertIn("technical_justification_needed", issue_types)
        self.assertIn("excessive_supplier_qualification", issue_types)
        self.assertTrue(any(finding.issue_type == "payment_acceptance_linkage" for finding in review.findings))
        self.assertTrue(any(finding.issue_type == "one_sided_commercial_term" for finding in review.findings))

    def test_review_flags_sample_scoring_weight_and_commercial_risk_shift(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "样品",
                "（1）材质好，质量好，做工优秀，完全满足采购单位需求，评审为优加 80 分；",
                "（2）材质一般，质量一般，做工一般，满足采购单位需求，评审为良加 50 分；",
                "（3）材质粗糙，质量及格，做工及格，符合采购单位需求，评审为中加 20 分；",
                "（4）材质差，质量差，做工差，不能满足采购单位需求，评审为差不加分。",
                "第三章 用户需求书",
                "商务要求",
                "★2.5 中标后，实际供货均需满足投标文件及国家标准要求，否则采购人有权拒绝收货，相关损失及责任均与采购人无关。",
                "3.3 中标人负责安装、调试。安装调试中发生的一切事故，相关责任全部由供应商承担，采购人对此不承担任何责任。",
                "3.4 中标人在供货、运输及安装等阶段应为人员负全部安全责任，安装期间发生意外均由中标人负全责。",
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
        self.assertTrue(
            any(
                finding.problem_title in {
                    "付款条件与履约评价结果深度绑定且评价标准开放",
                    "验收送检、检测和专家评审费用整体转嫁给供应商",
                    "商务责任和违约后果设置明显偏重",
                    "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担",
                }
                for finding in review.findings
            )
        )
        self.assertEqual(sum(1 for finding in review.findings if "样品评分主观性强且分值过高" in finding.problem_title), 1)
        self.assertGreaterEqual(sum(1 for finding in review.findings if finding.issue_type == "one_sided_commercial_term"), 1)

    def test_review_adds_scoring_structure_imbalance_when_multiple_high_weight_categories_exist(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "样品",
                "（1）材质好，质量好，做工优秀，完全满足采购单位需求，评审为优加 80 分；",
                "认证证书",
                "投标人通过质量管理体系认证得33分；投标人通过职业健康安全管理体系认证得33分；投标人通过环境管理体系认证得34分。",
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

        structure_findings = [finding for finding in review.findings if finding.issue_type == "scoring_structure_imbalance"]
        self.assertEqual(len(structure_findings), 1)
        self.assertIn("样品、认证和业绩", structure_findings[0].why_it_is_risky)
        self.assertEqual(structure_findings[0].risk_level, "high")

    def test_review_adds_subjective_scoring_theme_finding(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "实施方案",
                "①评审为优，得40分；②评审为良，得20分；③评审为中，得10分；④评审为差，得0分。",
                "项目管理方案",
                "①评审为优，得40分；②评审为良，得20分；③评审为中，得10分；④评审为差，得0分。",
                "接口理解",
                "①评审为优，得40分；②评审为良，得20分；③评审为中，得10分；④评审为差，得0分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="subjective123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        findings = [finding for finding in review.findings if "多个方案评分项大量使用主观分档" in finding.problem_title]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].risk_level, "high")

    def test_review_adds_demo_and_business_strength_theme_findings(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "演示",
                "如投标人通过可运行展示系统进行现场演示，每一分项内容全部完整演示并符合要求的得25分，最高得100分。",
                "如投标人使用系统原型、PPT或视频等方式进行现场演示，每一分项内容全部完整演示并符合要求的得15分，最高得50分。",
                "投标（谈判）供应商授权委托人请于本项目开标时间起60分钟内到达指定地点签到，迟到或缺席将会导致演示及答辩相关评分项得0分。",
                "商务部分",
                "投标人参与过国家相关标准委员会城市运行管理服务相关平台技术研究的得20分。",
                "投标人的注册资本200万以上加20分。",
                "投标人证明其近两年均为盈利状态，且年均营业收入不低于100万元，得20分。",
                "投标人证明其近两年均为盈利状态，且年均净利润不低于50万元，得20分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="demo123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        self.assertTrue(any("现场演示分值过高且签到要求形成额外门槛" in finding.problem_title for finding in review.findings))
        self.assertTrue(any("商务评分将企业背景和一般财务能力直接转化为高分优势" in finding.problem_title for finding in review.findings))

    def test_review_overall_summary_includes_document_level_risk_profile(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "供应商2024年度的纳税总额不得低于人民币500万元。",
                "营业执照的成立日期不得晚于2020年1月1日。",
                "评标信息",
                "演示",
                "如投标人通过可运行展示系统进行现场演示，每一分项内容全部完整演示并符合要求的得25分，最高得100分。",
                "投标（谈判）供应商授权委托人请于本项目开标时间起60分钟内到达指定地点签到，迟到或缺席将会导致演示及答辩相关评分项得0分。",
                "第三章 用户需求书",
                "付款方式",
                "其余阶段款项均将结合履约评价结果支付相应的款项。",
                "评价标准、评价指标以及分值项目负责人可根据项目要求自行设定。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="doc-level-profile",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("主风险重心集中在", review.overall_risk_summary)
        self.assertIn("评分标准", review.overall_risk_summary)
        self.assertIn("主问题包括", review.overall_risk_summary)

    def test_review_adds_commercial_chain_theme_finding(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "付款方式",
                "其余阶段款项均将结合履约评价结果支付相应的款项。",
                "评分为90分（含）以上的，支付全部对应款项。",
                "评分为60分以下的，对应阶段款不予支付，且采购人有权终止合同。",
                "评价标准、评价指标以及分值项目负责人可根据项目要求自行设定。",
                "服务期间如乙方连续两次被评级为“中”或累计扣款金额达到合同金额的30%，甲方有权解除合同。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="commercial123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        findings = [finding for finding in review.findings if "付款条件与履约评价结果深度绑定且评价标准开放" in finding.problem_title]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].risk_level, "high")
        self.assertEqual(findings[0].issue_type, "one_sided_commercial_term")

    def test_review_adds_domain_match_theme_findings_for_information_system_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：民生诉求服务平台（二期）项目",
                "申请人的资格要求",
                "投标人须具有特种设备安全管理和作业人员证书。",
                "评标信息",
                "投标人同时具有有效的质量管理体系认证证书（认证范围为：客户服务、园区保洁、设施维修、安防管理）。",
                "商务要求",
                "中标人应负责园区保洁、设施维修及安防管理服务。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/民生诉求服务平台项目.docx",
            document_name="民生诉求服务平台项目.docx",
            file_hash="domain123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        self.assertTrue(any("资格条件中存在与标的域不匹配的资质或登记要求" in finding.problem_title for finding in review.findings))
        self.assertTrue(any("评分项中存在与标的域不匹配的证书认证或模板内容" in finding.problem_title for finding in review.findings))

    def test_review_adds_template_domain_theme_for_textile_goods_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：低值易耗物品采购",
                "商务要求",
                "中标人提供的芯片及系统需无缝对接采购人现有系统。",
                "如提供货物与实际需求不符，以采购人的实际需求为准。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/低值易耗物品采购.docx",
            document_name="低值易耗物品采购.docx",
            file_hash="domain456",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        self.assertTrue(any("文件中存在与标的域不匹配的模板残留或义务外扩" in finding.problem_title for finding in review.findings))

    def test_review_flags_geographic_and_personnel_restrictions(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "投标人须在项目所在地设有常驻服务机构或办公场所，并配备本地服务团队。",
                "项目经理年龄不超过35岁，限男性，身高175cm以上。",
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
        self.assertIn("geographic_restriction", issue_types)
        self.assertIn("personnel_restriction", issue_types)

    def test_review_flags_business_chain_and_technical_justification_points(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "技术要求",
                "投标人须提供2024年1月1日至投标截止日前由第三方CMA或CNAS机构出具的阻燃、抗菌、抗病毒检测报告。",
                "兼容原有设备及专有接口平台。",
                "商务要求",
                "货物验收合格且财政资金到位后支付合同价款；抽检不合格复检费用由供应商承担，整改后重新验收。",
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
        self.assertIn("technical_justification_needed", issue_types)
        self.assertIn("narrow_technical_parameter", issue_types)
        self.assertIn("payment_acceptance_linkage", issue_types)
        self.assertIn("unclear_acceptance_standard", issue_types)

    def test_review_flags_geographic_scoring_and_contract_penalty_terms(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "项目实施方案",
                "如果在省内、本地存在相关项目的业绩，可得10分；在项目所在地设有服务机构并配备本地服务团队的，可得10分。",
                "商务要求",
                "采购人有权单方解除合同且无需承担责任。",
                "中标人违约的，采购人可按合同总金额20%支付违约金，并从应付货款中直接扣除。",
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
        self.assertIn("geographic_restriction", issue_types)
        self.assertIn("one_sided_commercial_term", issue_types)

    def test_review_merges_technical_justification_by_theme(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "技术要求",
                "须提供第三方CMA机构出具的阻燃检测报告。",
                "须提供第三方CNAS机构出具的抗菌检测报告。",
                "须提供第三方CMA机构出具的有机锡和邻苯检测报告。",
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

        justifications = [finding for finding in review.findings if finding.issue_type == "technical_justification_needed"]
        self.assertEqual(len(justifications), 1)
        self.assertIn("必要性论证", justifications[0].problem_title)

    def test_review_flags_one_hour_arrival_as_geographic_restriction(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "售后服务",
                "投标人承诺 1小时（60分钟）内到达现场处理问题的得100分，1.5小时（90分钟）内到达现场的得50分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="geo123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        findings = [finding for finding in review.findings if finding.issue_type == "geographic_restriction"]
        self.assertEqual(len(findings), 1)
        self.assertIn("属地倾斜", findings[0].problem_title)

    def test_review_merges_scoring_content_mismatch_by_theme(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "施工组织方案及安全保障措施",
                "发电机组安装的工程案例。",
                "投标人须提供具有CMA标识的第三方检测报告。",
                "投标人从业人员超过100人的，得3分；资产总额达到3000万元以上的，得3分；成立时间满3年的得2分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="scoremerge123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        mismatches = [finding for finding in review.findings if finding.issue_type == "scoring_content_mismatch"]
        self.assertEqual(len(mismatches), 1)
        self.assertTrue(
            "同一评分项已合并" in mismatches[0].problem_title
            or mismatches[0].problem_title == "评分项名称、内容和评分证据之间不一致"
        )

    def test_review_refines_fixed_year_technical_justification_text(self) -> None:
        text = "\n".join(
            [
                "技术要求",
                "产品应选用原装产品，生产日期必须是2025年。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="fixedyear123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        findings = [finding for finding in review.findings if finding.issue_type == "technical_justification_needed"]
        self.assertEqual(len(findings), 1)
        self.assertIn("固定年份", findings[0].problem_title)
        self.assertIn("市场可得性", findings[0].why_it_is_risky)
        self.assertIn("建议论证方向", findings[0].why_it_is_risky)

    def test_review_orders_high_risk_findings_before_medium_risk_findings(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "样品",
                "评审为优加 80 分；评审为良加 50 分；评审为中加 20 分。",
                "申请人的资格要求",
                "投标人须有A级有害生物防制（治）服务企业资质证书。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="sort123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = build_review_result(document, run_rule_scan(document))

        self.assertGreaterEqual(len(review.findings), 2)
        self.assertEqual(review.findings[0].risk_level, "high")

    def test_review_flags_geographic_restriction_in_service_response_clause(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "商务要求",
                "中标人须在项目所在地设有常驻服务人员，并配备本地服务团队，深圳市内2小时内到场处理故障。",
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

        self.assertTrue(any(finding.issue_type == "geographic_restriction" for finding in review.findings))

    def test_review_recognizes_tcm_procurement_bundle_issues(self) -> None:
        text = "\n".join(
            [
                "项目名称：北京大学深圳医院中药配方颗粒项目",
                "申请人的资格要求",
                "供应商成立日期必须早于2022年1月1日。",
                "供应商最近三个会计年度的年均纳税总额不低于300万元人民币。",
                "投标人必须提供最近连续三个月的月均参保人数不少于50人的证明。",
                "供应商2024年末经审计的资产总额不得低于人民币5000万元。",
                "供应商的主要经营地址必须位于福州市主城四区范围内。",
                "企业必须具备棉花加工资格认定并提供相关证书。",
                "投标人认证情况",
                "投标人具有IT服务管理体系认证。",
                "投标人具有生活垃圾分类服务认证证书。",
                "投标人具有SPCA三级以上证书。",
                "投标人具有有害生物防制（治）B级服务企业资质证书。",
                "用户需求书",
                "投标人承诺提供与采购人业务规模相适应的信息化管理系统，并开发系统端口与医院综合业务协同平台无缝对接。",
                "安排专人对信息管理系统进行管理维护，进行药瓶清洁。",
                "中药配方颗粒设备需求参数",
                "投标产品需提供国家级检测中心出具的检验报告，产品需符合GB 15605-2024检测标准。",
                "产品符合QB/T 1649-2024《聚苯乙烯泡沫包装材料》检测标准，并出具对应的检测报告。",
                "履约担保",
                "以现金形式缴纳采购预算的5%作为履约保证金。",
                "履约保证金在项目验收合格后不予退还，自动转为售后服务保证金，直至产品质保期结束（36个月）后方可申请退还。",
                "第四章 投标文件组成要求及格式",
                "1.6 对于已确认的中标药品，中标人在合同期内不得停止履约。否则，采购人有权单方解除合同。",
                "第三章 用户需求书",
                "1.6 对于已确认的中标药品，中标人在合同期内不得停止履约。否则，采购人有权单方解除合同。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/北京大学深圳医院中药配方颗粒项目.docx",
            document_name="北京大学深圳医院中药配方颗粒项目.docx",
            file_hash="tcm-bundle",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件设置一般财务和规模门槛", titles)
        self.assertIn("资格条件设置经营年限、属地场所或单项业绩门槛", titles)
        self.assertIn("资格条件中存在与标的域不匹配的行业资质或专门许可", titles)
        self.assertIn("技术要求引用了与标的不匹配的标准或规范", titles)
        self.assertIn("技术证明材料形式要求过严且带有地方化限制", titles)
        self.assertIn("商务条款设置异常资金占用安排", titles)
        self.assertIn("混合采购场景叠加自动化设备和信息化接口义务，边界不清", titles)
        self.assertLessEqual(
            sum(1 for finding in review.findings if "不得停止履约" in (finding.source_text or "")),
            1,
        )

    def test_review_separates_qualification_mismatch_from_template_mismatch(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "投标人须具备生活垃圾分类服务认证证书。",
                "投标人须具备公司治理评级证书。",
                "投标人须具备《合规管理体系认证证书》。",
                "第三章 用户需求书",
                "商务要求",
                "中标人应负责园区保洁、设施维修及安防管理服务。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="平台运营项目.docx",
            file_hash="qual-vs-template",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertTrue(
            "资格条件中存在与标的域不匹配的资质或登记要求" in titles
            or "资格条件中存在与标的域不匹配的行业资质或专门许可" in titles
        )
        self.assertIn("文件中存在与标的域不匹配的模板残留或义务外扩", titles)

    def test_review_adds_software_copyright_and_experience_scoring_themes(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "商务部分",
                "自主知识产权评价",
                "投标人具有城市大数据服务运营类计算机软件著作权登记证书，每提供一类得20分，最高得100分。",
                "经验评价",
                "投标人具有国家机关或事业单位委托的智慧城市或政府公共服务平台相关运营类项目经验且履约评价为满意或优秀或其他同等评价的，每提供一个得10分，最高得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="平台运营项目.docx",
            file_hash="software-exp-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("软件著作权评分过高且与履约能力评价边界不清", titles)
        self.assertIn("经验评价叠加主观履约评价证明且分值过高", titles)

    def test_review_recognizes_medical_device_qualification_and_mixed_scope_issues(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求：",
                "11. 农民专业合作社不具备投标资格。",
                "12. 投标人须具备高空清洗悬吊作业企业安全生产证书。",
                "13. 投标人须具备高新技术企业证书。",
                "14. 投标人须具备《企业诚信管理体系认证证书》。",
                "第三章 用户需求书",
                "其他",
                "中标人应免费开放软件端口，无偿派人配合与医院信息系统（包括但不限于HIS、PACS、LIS）的连接工作。",
                "合同签订后30个日历天内提供碳足迹盘查报告，并持续提交碳足迹改进报告。",
                "招标技术要求",
                "依据EN14175-3:2019标准。",
                "检验检测内容符合ISO 20743抗菌+ISO 10993。",
                "需提供经广告审查机关备案的产品彩页或带有CMA标志的检验检测报告及全国认证认可信息公共服务平台截图。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="深圳市宝安区中心医院血透类设备采购项目.docx",
            file_hash="medical-device-domain",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件中存在与标的域不匹配的行业资质或专门许可", titles)
        self.assertIn("资格条件整体超出法定准入和履约必需范围", titles)
        self.assertIn("技术要求引用了与标的不匹配的标准或规范", titles)
        self.assertIn("技术证明材料形式要求过严且带有地方化限制", titles)
        self.assertIn("设备采购中叠加医院信息系统开放对接义务，边界需复核", titles)
        self.assertIn("设备采购中叠加碳足迹盘查和持续改进义务，边界需复核", titles)
        self.assertNotIn("设备采购场景叠加信息化接口和碳足迹义务，边界不清", titles)
        self.assertNotIn("文件中存在与标的域不匹配的模板残留或义务外扩", titles)
        self.assertIn("货物采购并含安装调试项目", review.overall_risk_summary)

    def test_review_adds_qualification_reasoning_for_endoscope_style_thresholds(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求",
                "投标单位须为外商投资及民营企业，国资企业不具备投标资格。",
                "供应商注册资本不低于100万元。同时，供应商年收入不低于50万元，净利润不低于20万元。",
                "该企业的股权结构由国有资本持股51%以确保控股地位。经营年限不低于10年。",
                "投标人必须是经认定的国家级高新技术企业。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="胃肠镜项目.docx",
            file_hash="endoscope-qual",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件设置一般财务和规模门槛", titles)
        self.assertIn("资格条件设置经营年限、属地场所或单项业绩门槛", titles)
        self.assertIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_review_does_not_raise_property_special_equipment_certificate_to_qualification_total(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院物业管理服务",
                "第一章 招标公告",
                "申请人的资格要求",
                "投标人须配备取得特种设备安全管理和作业人员证书的项目人员。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="property-qualification-prefix",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("资格条件中存在与标的域不匹配的行业资质或专门许可", titles)
        self.assertNotIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_review_adds_signage_it_security_certificates_as_qualification_domain_mismatch(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院导视标识和宣传印刷服务",
                "第一章 招标公告",
                "申请人的资格要求",
                "投标人须具备IT服务管理体系认证证书、保安服务认证证书和信息安全管理体系认证证书。",
                "投标人注册地址须位于项目所在地并设有固定服务场所。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院导视标识和宣传印刷服务.docx",
            document_name="医院导视标识和宣传印刷服务.docx",
            file_hash="signage-qualification-prefix",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件中存在与标的域不匹配的行业资质或专门许可", titles)
        self.assertIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_review_uses_furniture_strategy_profile_for_furniture_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：宝城小学办公家具采购",
                "评标信息",
                "设计图方案内容完整，设计合理、实用性强的，评审为优，得70分。",
                "经验评价",
                "2022年1月1日以来，投标人具有家具类项目供货业绩且验收合格的，每提供一项得50分，本项最高得100分。",
                "商务要求",
                "在免费保修期内，一旦发生质量问题，中标人保证在接到通知4小时内赶到现场进行修理或更换。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/宝城小学办公家具采购.docx",
            document_name="宝城小学办公家具采购.docx",
            file_hash="furniture-strategy",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("货物采购并含安装调试项目", review.overall_risk_summary)
        self.assertIn("办公或医用家具供货、安装和售后保障类", review.overall_risk_summary)

    def test_review_ignores_template_guidance_for_furniture_template_mismatch(self) -> None:
        text = "\n".join(
            [
                "项目名称：办公家具采购",
                "用户需求书",
                "如有方案表述中有出现类似可实现、实现、可支持、支持等描述的，均表示方案需要实现的功能或应满足的要求。",
                "投标书编制软件",
                "使用投标文件制作专用软件编制并上传投标文件。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/办公家具采购.docx",
            document_name="办公家具采购.docx",
            file_hash="furniture-template",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("文件中存在与标的域不匹配的模板残留或义务外扩", titles)

    def test_review_adds_goods_capacity_scoring_theme_for_furniture_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：办公家具采购",
                "评标信息",
                "经验评价",
                "2022年1月1日以来，投标人具有家具类项目供货业绩且验收合格的，每提供一项得50分，本项最高得100分。",
                "生产设备情况",
                "投标人或核心产品制造商每具有以上一种相关设备的得10分，本项最高得100分。",
                "相关认证情况",
                "以上累计得分，最高得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/办公家具采购.docx",
            document_name="办公家具采购.docx",
            file_hash="furniture-scoring-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("经验评价、生产设备和认证因素高分集中并偏离核心供货能力", titles)
        self.assertIn("单一评分因素权重设置过高（同一评分项已合并）", titles)

    def test_review_adds_furniture_production_capacity_theme(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院办公家具采购",
                "评标信息",
                "技术保障措施",
                "投标人或所投核心产品制造商具有以下生产设备：数控剪板机、自动化生产线、异性海绵切割机；每提供一项生产设备得10分，最高得100分。",
                "若为自有设备，提供购买合同和发票；若为租赁设备，提供租赁合同、租赁发票和租赁方购买设备发票。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院办公家具采购.docx",
            document_name="医院办公家具采购.docx",
            file_hash="furniture-production-capacity",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("生产设备和制造能力直接高分赋值且与核心履约评价边界不清", titles)

    def test_review_adds_sample_submission_barrier_theme_for_furniture_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院办公家具采购",
                "评标信息",
                "样品",
                "每提供一件符合样品清单要求的样品得20分，最高得80分；评审为优加20分，评审为良加10分。",
                "六、样品要求",
                "样品递交签到：投标供应商授权人需在开标当日9:00-9:30到签到地点进行样品递交签到。",
                "上述资料提供不齐全，不予签到；签到时间截止后，不再受理签到；未进行签到的，样品不予接收。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院办公家具采购.docx",
            document_name="医院办公家具采购.docx",
            file_hash="furniture-sample-signin",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("样品评分叠加递交签到和不接收机制形成额外门槛", titles)

    def test_review_distinguishes_dense_furniture_certifications_from_mismatch(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院办公家具采购",
                "评标信息",
                "认证情况",
                "质量管理体系认证证书、环境管理体系认证证书、职业健康安全管理体系认证证书（认证范围包含办公家具、钢制家具、软体家具）的，得20分。",
                "低VOCs家具产品认证证书、家具中有害物质限量认证证书、产品抗菌认证证书、产品防霉认证证书，每项得20分，上述证书全部提供得100分。",
                "如投标人距本项目开标之日的注册成立时间不足3个月，可承诺中标（成交）后4个月内取得以上认证证书。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院办公家具采购.docx",
            document_name="医院办公家具采购.docx",
            file_hash="furniture-certification-dense",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("认证评分项目过密且高分值集中", titles)
        self.assertNotIn("认证评分混入错位证书且高分值结构失衡", titles)
        self.assertFalse(any(finding.issue_type == "technical_justification_needed" and "认证" in (finding.source_text or "") for finding in review.findings))

    def test_review_uses_property_service_strategy_profile_for_property_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：西湾小学物业管理服务",
                "评分因素",
                "投标人具有以下认证证书，且认证范围包含物业管理内容，每提供一项有效认证的得34分，最高得100分。",
                "投标人具有同类项目物业管理服务经验的，每提供1个业绩得25分，最高得100分。",
                "每月10日前结算上月管理服务费。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/物业管理服务.docx",
            document_name="物业管理服务.docx",
            file_hash="property-strategy",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("物业管理或综合后勤服务项目", review.overall_risk_summary)
        self.assertIn("校园、医院或公共机构物业服务及驻场保障类", review.overall_risk_summary)

    def test_review_prefers_property_service_strategy_even_for_hospital_property_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：深圳市龙岗区人民医院物业管理服务",
                "评分因素",
                "投标人具有以下认证证书，且认证范围包含物业管理内容，每提供一项有效认证的得20分，最高得100分。",
                "物业服务人员须24小时值守并完成医院后勤保障。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="hospital-property-strategy",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("物业管理或综合后勤服务项目", review.overall_risk_summary)
        self.assertNotIn("医疗药品或医用配套采购项目", review.overall_risk_summary)

    def test_review_filters_property_service_environmental_contract_noise_from_technical_justification(self) -> None:
        text = "\n".join(
            [
                "项目名称：深圳市龙岗区人民医院物业管理服务",
                "五、技术要求",
                "4)负责回收医院内电池，按照深圳市环保相关要求进行处理。",
                "污水井、雨水井及时疏通清理，每月至少进行一次化粪池压榨清掏并消毒处理，作业符合环保要求。",
                "★六、商务要求",
                "因中标单位的过错，造成政府部门检查（包括但不限于环保、反恐、消防、医院评审检查等）不合格，对采购人造成重大影响的。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="hospital-property-technical-noise",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("安全环保类技术要求可能合理但需补充必要性论证", titles)

    def test_review_does_not_treat_property_core_service_terms_as_template_mismatch(self) -> None:
        text = "\n".join(
            [
                "项目名称：深圳市龙岗区人民医院物业管理服务",
                "评分因素",
                "保洁管理服务",
                "安保管理服务",
                "设施维修服务",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="hospital-property-template-noise",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("文件中存在与标的域不匹配的模板残留或义务外扩", titles)

    def test_review_requires_supplier_level_markers_for_qualification_umbrella(self) -> None:
        text = "\n".join(
            [
                "项目名称：深圳市龙岗区人民医院物业管理服务",
                "技术要求",
                "★所有上岗消杀人员持有有害生物防制员证或防治员证。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="hospital-property-qualification-noise",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("资格条件中存在与标的域不匹配的行业资质或专门许可", titles)
        self.assertNotIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_review_ignores_submission_appendix_financial_fields_for_qualification_themes(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "三、投标人情况及资格证明文件",
                "中小企业声明函（服务）",
                "从业人员、营业收入、资产总额按上年度数据填写。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/物业管理服务.docx",
            document_name="物业管理服务.docx",
            file_hash="property-appendix-qualification-noise",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("资格条件设置一般财务和规模门槛", titles)
        self.assertNotIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_review_skips_property_template_theme_for_scoring_side_software_items(self) -> None:
        text = "\n".join(
            [
                "项目名称：深圳市龙岗区人民医院物业管理服务",
                "评标信息",
                "评分因素",
                "物业垃圾分类自动化分拣类系统软件著作权，每提供一个得20分，最高得100分。",
                "物业能源管理类软件著作权，每提供一个得20分，最高得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="hospital-property-template-scoring-noise",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("物业服务场景叠加自动化系统和软件著作权评分，边界不清", titles)
        self.assertNotIn("文件中存在与标的域不匹配的模板残留或义务外扩", titles)

    def test_review_adds_property_service_experience_high_weight_theme(self) -> None:
        text = "\n".join(
            [
                "项目名称：深圳市龙岗区人民医院物业管理服务",
                "评标信息",
                "评分因素",
                "同类型项目业绩及履约评价",
                "医院物业管理项目履约评价为满意或优秀的，每提供1个得20分，最高得60分。",
                "具有三甲医院评审创建或复审经验的，每提供1个得20分，最高得40分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/医院物业管理服务.docx",
            document_name="医院物业管理服务.docx",
            file_hash="hospital-property-experience-weight",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("医院物业经验和医院评审经验评分高权重且叠加履约评价证明", titles)

    def test_review_drops_qualification_domain_mismatch_when_it_only_appears_in_scoring(self) -> None:
        finding = Finding(
            finding_id="F-001",
            document_name="物业管理服务.docx",
            problem_title="资格条件中出现与采购标的不匹配的资质要求",
            page_hint=None,
            clause_id="保洁主管评分",
            source_section="评分因素",
            section_path="评标信息-评分项-技术部分-评分因素",
            table_or_item_label="评分因素",
            text_line_start=1,
            text_line_end=1,
            source_text="具有相关机构颁发的有害生物防制员证书得5分",
            issue_type="qualification_domain_mismatch",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="",
            impact_on_competition_or_performance="",
            legal_or_policy_basis=None,
            rewrite_suggestion="",
            needs_human_review=True,
            human_review_reason="",
            finding_origin="rule",
        )

        filtered = _drop_false_positive_findings([finding])
        self.assertEqual([], filtered)

    def test_review_drops_property_service_post_certificate_single_point_from_qualification_mismatch(self) -> None:
        finding = Finding(
            finding_id="F-001",
            document_name="物业管理服务.docx",
            problem_title="资格条件中出现与采购标的不匹配的资质要求",
            page_hint=None,
            clause_id="★所有上岗消杀人员持有有害生物防制员证或防治员证",
            source_section="五、技术要求",
            section_path="第一章 招标公告-五、技术要求",
            table_or_item_label=None,
            text_line_start=2342,
            text_line_end=2342,
            source_text="★所有上岗消杀人员持有有害生物防制员证或防治员证。",
            issue_type="qualification_domain_mismatch",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky="",
            impact_on_competition_or_performance="",
            legal_or_policy_basis=None,
            rewrite_suggestion="",
            needs_human_review=True,
            human_review_reason="",
            finding_origin="rule",
        )

        filtered = _drop_false_positive_findings([finding])
        self.assertEqual([], filtered)

    def test_review_adds_service_scoring_mismatch_theme_for_endoscope_style_scoring(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "技术部分",
                "评分因素",
                "投标人承诺的售后服务内容和工作方案",
                "如果在医疗行业存在相关项目的业绩，可得10分。",
                "若供应商提供守合同重信用企业，可得10分。",
                "若供应商提供全国科技型中小企业证明，可以得10分。",
                "如果供应商提供营业执照或事业单位法人证书等证明资料扫描件，可得1分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="胃肠镜项目.docx",
            file_hash="endoscope-service-score",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("售后服务评分混入业绩、荣誉和资格材料", titles)

    def test_review_commercial_lifecycle_ignores_generic_contract_burden_words(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "商务要求",
                "在免费保修期内，中标人应在2小时内响应，12小时内到达现场维修，48小时内消除故障。",
                "若因为财政审批的原因造成采购人延期付款的，采购人不承担违约责任。",
                "如采购人需要，中标人需无条件配合采购人委托有资质的第三方质量检测部门进行技术参数检测确认。",
                "第五章 合同条款及格式",
                "乙方对其所销售的货物应当享有知识产权或经权利人合法授权，保证没有侵犯任何第三方的合法权益并承担相应责任。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="胃肠镜项目.docx",
            file_hash="endoscope-commercial",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        lifecycle = next(
            finding
            for finding in review.findings
            if finding.problem_title == "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担"
        )
        self.assertNotIn("知识产权", lifecycle.section_path)
        self.assertGreaterEqual(lifecycle.text_line_end, lifecycle.text_line_start)

    def test_review_commercial_lifecycle_prefers_dominant_business_chapter(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "★五、商务要求",
                "1.付款方式：验收合格后支付95%。",
                "2.如采购人需要，中标人需配合第三方质量检测，检测费用由中标人承担。",
                "3.中标人须2小时响应，12小时到达现场，48小时排除故障。",
                "第五章 合同条款及格式",
                "11.1 如乙方不履约，应承担违约责任。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="胃肠镜项目.docx",
            file_hash="endoscope-commercial-dominant",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        lifecycle = next(
            finding
            for finding in review.findings
            if finding.problem_title == "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担"
        )
        self.assertIn("第三章 用户需求书", lifecycle.section_path)
        self.assertNotIn("第五章 合同条款及格式", lifecycle.section_path)

    def test_review_certification_theme_requires_actual_certification_context(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "评分因素",
                "若供应商提供全国科技型中小企业证明，可以得10分。",
                "采用环保材料进行包装，需提供检测报告。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="胃肠镜项目.docx",
            file_hash="endoscope-cert-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("认证评分混入错位证书且高分值结构失衡", titles)

    def test_review_uses_catering_strategy_profile_for_canteen_project(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "深圳市某医院食堂托管服务采购项目",
                "负责职工食堂日常事务管理和供餐服务。",
                "评分因素",
                "投标人具有政府部门食堂管理服务类同类项目业绩并经采购单位考核评价为优或优秀的，每提供一项得25分，最高得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="食堂托管服务采购项目.docx",
            file_hash="canteen-strategy",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("餐饮托管或食堂运营服务项目", review.overall_risk_summary)
        self.assertIn("食堂托管、供餐保障", review.overall_risk_summary)

    def test_review_does_not_treat_24_hour_catering_service_as_geographic_restriction(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "根据医院整体规划，可提供24小时营业及就餐服务。",
                "负责食堂全年无休供餐保障。",
                "评分因素",
                "投标人具有政府部门食堂管理服务类同类项目业绩并经采购单位考核评价为优或优秀的，每提供一项得25分，最高得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="食堂托管服务采购项目.docx",
            file_hash="canteen-24h-service",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("驻场、短时响应或服务场地要求形成事实上的属地倾斜", titles)

    def test_review_adds_personnel_theme_for_catering_certificates(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "评分因素",
                "拟安排的项目负责人情况（仅限一人）",
                "具备高级餐饮业职业经理人证书、食品安全管理员证书。",
                "拟安排的项目主要团队成员（主要技术人员）情况",
                "具备中式烹调师或中式（西式）面点师证书。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="食堂托管服务采购项目.docx",
            file_hash="canteen-personnel-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("人员与团队评分混入错位证书并过度堆叠条件", titles)

    def test_review_adds_experience_theme_for_excellent_canteen_evaluation(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "评分因素",
                "投标人具有政府部门食堂管理服务类同类项目业绩并经采购单位考核评价为优或优秀的，每提供一项得25分，最高得100分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="食堂托管服务采购项目.docx",
            file_hash="canteen-experience-theme",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("经验评价叠加主观履约评价证明且分值过高", titles)

    def test_review_uses_textile_strategy_for_curtain_project_even_in_hospital_context(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院窗帘采购项目",
                "第三章 用户需求书",
                "本项目采购窗帘、隔帘及安装服务。",
                "评标信息",
                "供应商年收入不低于50万元，注册资本不低于100万元。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="龙岗区医院窗帘采购项目.docx",
            file_hash="textile-strategy",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("窗帘、隔帘、床品或被服供货、安装和售后保障类", review.overall_risk_summary)

    def test_review_does_not_add_scoring_semantic_theme_for_pure_report_formality_only(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "评分因素",
                "技术要求偏离情况",
                "提供检测报告扫描件（原件备查）以及检验检测机构官网查询截图作为得分依据。",
                "以投标人《技术要求偏离表》的响应情况及按要求提供相关检验报告为准。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="窗帘采购项目.docx",
            file_hash="pure-report-formality",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("评分项名称、内容和评分证据之间不一致", titles)

    def test_review_uses_signage_printing_strategy_for_hospital_signage_project(self) -> None:
        text = "\n".join(
            [
                "项目名称：坪山区人民医院标识标牌及宣传印制等服务项目",
                "第三章 用户需求书",
                "中标供应商应提供标识标牌、宣传品设计、文创产品设计，并具备 UV 打印机、喷绘机和写真机等设备保障。",
                "评标信息",
                "投标人具备 IT 服务管理体系认证、保安服务认证和信息安全管理体系认证的得分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage.docx",
            document_name="坪山区人民医院标识标牌及宣传印制等服务项目.docx",
            file_hash="signage-strategy",
            normalized_text_path="/tmp/signage.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        self.assertIn("标识标牌及宣传印制综合服务项目", review.overall_risk_summary)
        self.assertIn("医院、学校或公共机构标识导视、宣传印制和现场制作安装维护类", review.overall_risk_summary)

    def test_review_adds_signage_qualification_bundle_findings(self) -> None:
        text = "\n".join(
            [
                "第一章 招标公告",
                "申请人的资格要求：",
                "供应商必须在中国境内注册，且成立时间不少于五年。",
                "投标人必须提供税务或社保部门出具的证明文件，显示其最近连续三个月的月均参保人数不少于50人。",
                "其2024年末经审计的净资产（所有者权益）必须不低于2000万元。",
                "投标人2024年度实际缴纳的增值税及企业所得税合计金额必须超过200万元。",
                "供应商的营业执照注册地址必须位于福州市行政区域范围内。",
                "须具备学生饮用奶定点生产企业资格认定并提供相关证书。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage-qualification.docx",
            document_name="标识标牌及宣传印制服务项目.docx",
            file_hash="signage-qualification",
            normalized_text_path="/tmp/signage-qualification.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("资格条件设置一般财务和规模门槛", titles)
        self.assertIn("资格条件设置经营年限、属地场所或单项业绩门槛", titles)
        self.assertIn("资格条件中存在与标的域不匹配的行业资质或专门许可", titles)
        self.assertIn("资格条件整体超出法定准入和履约必需范围", titles)

    def test_review_ignores_explanatory_summary_clause_for_signage_scoring_noise(self) -> None:
        text = "\n".join(
            [
                "第三章 用户需求书",
                "10.投标供应商针对项目制定方案，包括不不限于：1.工作措施 2.工作流程 3.售后服务 4.应急事件处理预案；质量保障措施及方案；借助自身的质量管理体系、环境管理体系、职业健康安全管理体系、商品售后服务评价体系认证情况和标识标牌及印刷类软件著作权方面，对项目提供支撑进行高质量的服务要求。投标供应商中标后自有或租赁跟项目服务相关的 UV 打印机、喷绘机、写真机、有雕刻机、折弯机等关键设备保障项目的履约以及售后。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage-summary.docx",
            document_name="标识标牌及宣传印制服务项目.docx",
            file_hash="signage-summary",
            normalized_text_path="/tmp/signage-summary.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("评分项中存在与标的域不匹配的证书认证或模板内容", titles)
        self.assertNotIn("评分项名称、内容和评分证据之间不一致", titles)
        self.assertNotIn("技术要求可能合理但需补充必要性论证", titles)

    def test_catalog_routing_avoids_property_certificate_overreporting(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院物业管理服务项目",
                "申请人的资格要求",
                "项目负责人须持有特种设备安全管理和作业人员证书。",
                "服务内容包括医院物业、保洁、运送和驻场保障。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/property.docx",
            document_name="医院物业管理服务项目.docx",
            file_hash="property123",
            normalized_text_path="/tmp/property.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertNotIn("资格条件中存在与标的域不匹配的资质或登记要求", titles)

    def test_catalog_routing_flags_signage_it_certification_mismatch(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院标识标牌及宣传印制服务项目",
                "评标信息",
                "供应商具有IT服务管理体系认证证书、保安服务认证证书、信息安全管理体系认证证书的，每项得10分。",
                "供应商具有标识导视设计制作安装能力。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/signage-cert.docx",
            document_name="医院标识标牌及宣传印制服务项目.docx",
            file_hash="signage-cert",
            normalized_text_path="/tmp/signage-cert.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document))
        titles = {finding.problem_title for finding in review.findings}
        self.assertIn("评分项中存在与标的域不匹配的证书认证或模板内容", titles)

    def test_review_pipeline_supports_assist_parser_mode(self) -> None:
        text = "\n".join(
            [
                "项目名称：2025年省级全民健身工程（多功能运动场项目）",
                "评标信息",
                "技术部分满分78分。",
                "价格部分满分10分。",
                "每一项负偏离扣2分，扣完为止。",
                "提供CMA或CNAS检测报告的，每提供1项得2分。",
                "围网、硅PU面层和体育比赛用灯等运动场设施应满足采购需求。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/parser-assist.docx",
            document_name="parser-assist.docx",
            file_hash="parser-assist",
            normalized_text_path="/tmp/parser-assist.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )

        review = build_review_result(document, run_rule_scan(document), parser_mode="assist")
        self.assertTrue(review.findings)
        self.assertIn("技术评分权重过高且负偏离、专项检测加分进一步放大结构失衡", {finding.problem_title for finding in review.findings})
        self.assertTrue(any(finding.document_structure_type for finding in review.findings))


if __name__ == "__main__":
    unittest.main()
