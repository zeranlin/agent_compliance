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
        self.assertIn("评分项名称、内容和评分证据之间不一致", titles)

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
                "第三章 用户需求书",
                "交货期限",
                "★合同签订后1000个日历日内交货。",
                "安装、调试、验收及相关技术文件、资料",
                "所有与验收环节相关的报验、送检、检测报告出具及专家评审等费用，均应计入投标单价，由供应商自行消化。",
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
        self.assertIn("现场演示分值过高且签到要求形成额外门槛", titles)
        self.assertFalse(any("评分中设置与履约弱相关的荣誉资质加分" in title for title in titles))
        self.assertFalse(any("评分分档缺少明确量化锚点" in title for title in titles))
        self.assertFalse(any("单一评分因素权重设置过高" in title for title in titles))

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
                }
                for finding in review.findings
            )
        )
        self.assertEqual(sum(1 for finding in review.findings if "样品评分主观性强且分值过高" in finding.problem_title), 1)
        self.assertEqual(sum(1 for finding in review.findings if finding.issue_type == "one_sided_commercial_term"), 1)

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
        self.assertIn("商务与验收", review.overall_risk_summary)
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
        self.assertTrue(any("文件中存在与标的域不匹配的模板残留或义务外扩" in finding.problem_title for finding in review.findings))

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
        self.assertIn("文件中存在与标的域不匹配的模板残留或义务外扩", titles)
        self.assertLessEqual(
            sum(1 for finding in review.findings if "不得停止履约" in (finding.source_text or "")),
            1,
        )


if __name__ == "__main__":
    unittest.main()
