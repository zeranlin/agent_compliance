from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from agent_compliance.cli import build_parser
from agent_compliance.config import LLMConfig, detect_llm_config
from agent_compliance.knowledge.procurement_catalog import classify_procurement_catalog
from agent_compliance.pipelines.llm_enhance import _build_prompt, enhance_review_result
from agent_compliance.pipelines.llm_review import _build_task_prompt, apply_llm_review_tasks, run_benchmark_gate
from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.schemas import Finding, NormalizedDocument, ReviewResult
from agent_compliance.web.app import _web_llm_config


class LLMIntegrationTest(unittest.TestCase):
    def test_review_parser_supports_explicit_llm_switch(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["review", "/tmp/sample.txt", "--use-llm", "--llm-model", "qwen-local"])
        self.assertTrue(args.use_llm)
        self.assertEqual(args.llm_model, "qwen-local")

    def test_enhance_review_result_is_noop_when_llm_disabled(self) -> None:
        review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[
                Finding(
                    finding_id="F-001",
                    document_name="sample.txt",
                    problem_title="技术参数组合存在定向或过窄风险",
                    page_hint=None,
                    clause_id="1.1",
                    source_section="技术要求",
                    section_path="第三章 用户需求书-技术要求",
                    table_or_item_label=None,
                    text_line_start=10,
                    text_line_end=10,
                    source_text="具备无线插拔技术、无线连接技术。",
                    issue_type="narrow_technical_parameter",
                    risk_level="medium",
                    severity_score=2,
                    confidence="medium",
                    compliance_judgment="needs_human_review",
                    why_it_is_risky="old",
                    impact_on_competition_or_performance="impact",
                    legal_or_policy_basis=None,
                    rewrite_suggestion="rewrite",
                    needs_human_review=True,
                    human_review_reason="reason",
                )
            ],
            items_for_human_review=[],
            review_limitations=[],
        )
        llm_config = LLMConfig(
            enabled=False,
            base_url="http://112.111.54.86:10011/v1",
            model="local-model",
            api_key=None,
            timeout_seconds=60,
        )

        result = enhance_review_result(review, llm_config)
        self.assertEqual(result.findings[0].problem_title, review.findings[0].problem_title)
        self.assertEqual(result.findings[0].why_it_is_risky, review.findings[0].why_it_is_risky)

    def test_detect_llm_config_loads_local_env_defaults(self) -> None:
        for key in [
            "AGENT_COMPLIANCE_LLM_ENABLED",
            "AGENT_COMPLIANCE_LLM_BASE_URL",
            "AGENT_COMPLIANCE_LLM_MODEL",
            "AGENT_COMPLIANCE_LLM_API_KEY",
        ]:
            os.environ.pop(key, None)

        config = detect_llm_config()
        self.assertEqual(config.base_url, "http://112.111.54.86:10011/v1")
        self.assertEqual(config.model, "qwen3.5-27b")
        self.assertEqual(config.api_key, "local-dev-placeholder")

    def test_web_llm_switch_overrides_disabled_env_default(self) -> None:
        os.environ["AGENT_COMPLIANCE_LLM_ENABLED"] = "false"
        config = _web_llm_config(True)
        self.assertTrue(config.enabled)

    def test_llm_prompt_only_targets_technical_findings(self) -> None:
        review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[
                Finding(
                    finding_id="F-001",
                    document_name="sample.txt",
                    problem_title="技术参数组合存在定向或过窄风险",
                    page_hint=None,
                    clause_id="1.1",
                    source_section="技术要求",
                    section_path="第三章 用户需求书-技术要求",
                    table_or_item_label=None,
                    text_line_start=10,
                    text_line_end=10,
                    source_text="具备无线插拔技术、无线连接技术。",
                    issue_type="narrow_technical_parameter",
                    risk_level="medium",
                    severity_score=2,
                    confidence="medium",
                    compliance_judgment="needs_human_review",
                    why_it_is_risky="old",
                    impact_on_competition_or_performance="impact",
                    legal_or_policy_basis=None,
                    rewrite_suggestion="rewrite",
                    needs_human_review=True,
                    human_review_reason="reason",
                ),
                Finding(
                    finding_id="F-002",
                    document_name="sample.txt",
                    problem_title="资格条件设置与履约关联不足",
                    page_hint=None,
                    clause_id="2.1",
                    source_section="资格要求",
                    section_path="第一章 招标公告-申请人的资格要求",
                    table_or_item_label=None,
                    text_line_start=20,
                    text_line_end=20,
                    source_text="投标单位须为外商投资及民营企业。",
                    issue_type="excessive_supplier_qualification",
                    risk_level="high",
                    severity_score=3,
                    confidence="high",
                    compliance_judgment="likely_non_compliant",
                    why_it_is_risky="old",
                    impact_on_competition_or_performance="impact",
                    legal_or_policy_basis=None,
                    rewrite_suggestion="rewrite",
                    needs_human_review=False,
                    human_review_reason=None,
                ),
            ],
            items_for_human_review=[],
            review_limitations=[],
        )
        prompt = _build_prompt(review.document_name, [review.findings[0]])
        self.assertIn("F-001", prompt)
        self.assertNotIn("F-002", prompt)

    def test_llm_review_tasks_add_findings_and_generate_candidates(self) -> None:
        text = "\n".join(
            [
                "低值易耗物品采购",
                "评标信息",
                "样品",
                "5.1 优：样品外观整洁无破损，生产工艺很好，材料质感很好，样品整体制作效果很好，得80%分。",
                "环境标志产品认证",
                "6.1 投标人提供环境标志产品认证得100%分。",
                "商务要求",
                "9.6 中标人提供的芯片及系统需无缝对接医院现有的设备及系统。",
                "9.7 如提供货物与实际需求不符，以采购人的实际需求为准。",
                "验收",
                "5.4 如投标人届时不派人来，则验收结果应以采购人的验收报告为最终验收结果。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="llm12345",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[],
            items_for_human_review=[],
            review_limitations=[],
        )
        llm_config = LLMConfig(
            enabled=True,
            base_url="http://112.111.54.86:10011/v1",
            model="local-model",
            api_key=None,
            timeout_seconds=60,
        )
        responses = [
            '{"findings":[{"should_flag":true,"clause_ref":"6:6.1","clause_id":"6.1","issue_type":"scoring_content_mismatch","problem_title":"评分项内容与采购标的不完全匹配","why_it_is_risky":"认证条款与当前采购标的直接履约关联不足。","rewrite_suggestion":"删除与标的不直接相关的评分内容。"}]}',
            '{"findings":[{"should_flag":true,"clause_ref":"8:9.6","clause_id":"9.6","issue_type":"template_mismatch","problem_title":"条款疑似跨领域模板错贴","why_it_is_risky":"芯片及系统对接与纺织类货物采购标的不一致。","rewrite_suggestion":"删除系统对接要求。"}]}',
            '{"findings":[{"should_flag":true,"clause_ref":"4:5.1","clause_id":"5.1","issue_type":"ambiguous_requirement","problem_title":"样品评分主观性强且缺少量化锚点","why_it_is_risky":"样品评分使用优良中差主观分档，评委自由裁量空间过大。","rewrite_suggestion":"将样品评分拆成可核验指标。"}]}',
            '{"findings":[{"should_flag":true,"clause_ref":"11:5.4","clause_id":"5.4","issue_type":"unclear_acceptance_standard","problem_title":"验收结果单方确定且需求边界开放","why_it_is_risky":"验收结果完全由采购人单方确认，且实际需求边界不清。","rewrite_suggestion":"明确复验和异议处理机制。"}]}',
        ]

        with patch("agent_compliance.pipelines.llm_review.OpenAICompatibleLLMClient.chat", side_effect=responses):
            result, artifacts = apply_llm_review_tasks(document, review, llm_config, output_stem="llmtest")

        self.assertGreaterEqual(len(result.findings), 4)
        self.assertGreaterEqual(len(artifacts.added_findings), 4)
        self.assertGreaterEqual(len(artifacts.rule_candidates), 4)
        self.assertTrue(Path(artifacts.candidate_json_path).exists())
        self.assertTrue(Path(artifacts.benchmark_json_path).exists())
        self.assertTrue(Path(artifacts.difference_json_path).exists())
        self.assertTrue(Path(artifacts.difference_md_path).exists())
        self.assertEqual(artifacts.difference_learning["status"], "ok")
        self.assertIn("当前结果已接入本地规则映射、引用资料检索和本地大模型边界判断", result.overall_risk_summary)

        for path in [
            artifacts.candidate_json_path,
            artifacts.candidate_md_path,
            artifacts.benchmark_json_path,
            artifacts.benchmark_md_path,
            artifacts.difference_json_path,
            artifacts.difference_md_path,
        ]:
            Path(path).unlink(missing_ok=True)

    def test_benchmark_gate_marks_unknown_issue_types(self) -> None:
        gate = run_benchmark_gate(
            [
                {
                    "candidate_rule_id": "CAND-001",
                    "issue_type": "template_mismatch",
                },
                {
                    "candidate_rule_id": "CAND-002",
                    "issue_type": "unknown_issue_type",
                },
            ]
        )
        self.assertEqual(gate["candidate_count"], 2)
        self.assertEqual(gate["covered_count"], 1)
        self.assertEqual(gate["needs_benchmark_count"], 1)
        self.assertEqual(gate["status"], "needs_attention")

    def test_llm_added_fragment_is_arbitrated_under_existing_theme_finding(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "技术服务方案",
                "方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。",
                "实施方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。",
                "培训方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="arbiter123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        base_review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[
                Finding(
                    finding_id="F-001",
                    document_name="sample.txt",
                    problem_title="多个方案评分项大量使用主观分档且缺少量化锚点",
                    page_hint=None,
                    clause_id=clauses[1].clause_id,
                    source_section=clauses[1].source_section or "",
                    section_path=clauses[1].section_path,
                    table_or_item_label=clauses[1].table_or_item_label,
                    text_line_start=clauses[1].line_start,
                    text_line_end=clauses[-1].line_end,
                    source_text="方案评审为优得 10 分 等3项",
                    issue_type="scoring_structure_imbalance",
                    risk_level="high",
                    severity_score=3,
                    confidence="high",
                    compliance_judgment="likely_non_compliant",
                    why_it_is_risky="主题问题",
                    impact_on_competition_or_performance="impact",
                    legal_or_policy_basis=None,
                    rewrite_suggestion="rewrite",
                    needs_human_review=False,
                    human_review_reason=None,
                    finding_origin="analyzer",
                )
            ],
            items_for_human_review=[],
            review_limitations=[],
        )
        llm_config = LLMConfig(
            enabled=True,
            base_url="http://112.111.54.86:10011/v1",
            model="local-model",
            api_key=None,
            timeout_seconds=60,
        )
        responses = [
            '{"findings":[]}',
            '{"findings":[]}',
            '{"findings":[{"should_flag":true,"clause_ref":"3:方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。","clause_id":"方案评审为优得 10 分，评审为良得 6 分，评审为中得 2 分。","issue_type":"ambiguous_requirement","problem_title":"评分分档缺少明确量化锚点","why_it_is_risky":"主观分档问题。","rewrite_suggestion":"量化。"}]}',
            '{"findings":[]}',
        ]

        with patch("agent_compliance.pipelines.llm_review.OpenAICompatibleLLMClient.chat", side_effect=responses):
            result, artifacts = apply_llm_review_tasks(document, base_review, llm_config, output_stem="arbiterllm")

        titles = [finding.problem_title for finding in result.findings]
        self.assertIn("多个方案评分项大量使用主观分档且缺少量化锚点", titles)
        self.assertNotIn("评分分档缺少明确量化锚点", titles)
        self.assertGreaterEqual(len(artifacts.added_findings), 1)

        for path in [
            artifacts.candidate_json_path,
            artifacts.candidate_md_path,
            artifacts.benchmark_json_path,
            artifacts.benchmark_md_path,
            artifacts.difference_json_path,
            artifacts.difference_md_path,
        ]:
            Path(path).unlink(missing_ok=True)

    def test_llm_review_tasks_fallback_adds_scoring_and_commercial_findings(self) -> None:
        text = "\n".join(
            [
                "评标信息",
                "样品",
                "5.1 优：样品外观整洁无破损，生产工艺很好，材料质感很好，样品整体制作效果很好，得80%分。",
                "认证证书",
                "6.1 投标人提供环境标志产品认证得100%分。",
                "商务要求",
                "5.4 如投标人届时不派人来，则验收结果应以采购人的验收报告为最终验收结果。",
                "9.7 如提供货物与实际需求不符，以采购人的实际需求为准。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="fallback123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[],
            items_for_human_review=[],
            review_limitations=[],
        )
        llm_config = LLMConfig(
            enabled=True,
            base_url="http://112.111.54.86:10011/v1",
            model="local-model",
            api_key=None,
            timeout_seconds=60,
        )

        with patch("agent_compliance.pipelines.llm_review.OpenAICompatibleLLMClient.chat", return_value='{"findings":[]}'):
            result, artifacts = apply_llm_review_tasks(document, review, llm_config, output_stem="llmfallback")

        issue_types = {finding.issue_type for finding in artifacts.added_findings}
        self.assertIn("ambiguous_requirement", issue_types)
        self.assertIn("scoring_structure_imbalance", issue_types)
        self.assertIn("unclear_acceptance_standard", issue_types)

        for path in [
            artifacts.candidate_json_path,
            artifacts.candidate_md_path,
            artifacts.benchmark_json_path,
            artifacts.benchmark_md_path,
            artifacts.difference_json_path,
            artifacts.difference_md_path,
        ]:
            Path(path).unlink(missing_ok=True)

    def test_document_audit_fallback_adds_chapter_level_theme_findings(self) -> None:
        text = "\n".join(
            [
                "柴油发电机组采购及安装项目",
                "申请人的资格要求",
                "投标人须提供有害生物防制服务机构资质证书。",
                "投标人年均纳税额不低于50万元。",
                "评标信息",
                "施工组织方案及安全保障措施",
                "发电机组安装的工程案例。",
                "投标人须提供具有CMA标识的第三方检测报告。",
                "商务条款",
                "采购人不承担任何责任。",
                "项目正常运行三个月后支付尾款。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="docaudit123",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[],
            items_for_human_review=[],
            review_limitations=[],
        )
        llm_config = LLMConfig(
            enabled=True,
            base_url="http://112.111.54.86:10011/v1",
            model="local-model",
            api_key=None,
            timeout_seconds=60,
        )

        with patch("agent_compliance.pipelines.llm_review.OpenAICompatibleLLMClient.chat", return_value='{"findings":[]}'):
            result, artifacts = apply_llm_review_tasks(document, review, llm_config, output_stem="docauditfallback")

        titles = {finding.problem_title for finding in artifacts.added_findings}
        self.assertIn("资格章节存在与标的不匹配的资质要求或一般经营门槛", titles)
        self.assertIn("评分或资质条款中存在与标的域不匹配的证书、案例或模板内容", titles)
        self.assertIn("商务章节存在付款绑定、责任失衡或验收边界不清问题", titles)
        self.assertTrue(any(finding.risk_level == "high" for finding in artifacts.added_findings))
        self.assertTrue(any("资格章节存在与标的不匹配的资质要求或一般经营门槛" == finding.problem_title for finding in result.findings))

        for path in [
            artifacts.candidate_json_path,
            artifacts.candidate_md_path,
            artifacts.benchmark_json_path,
            artifacts.benchmark_md_path,
            artifacts.difference_json_path,
            artifacts.difference_md_path,
        ]:
            Path(path).unlink(missing_ok=True)

    def test_document_audit_prompt_includes_catalog_summary(self) -> None:
        text = "\n".join(
            [
                "项目名称：医院导视标识和宣传印刷服务",
                "采购内容：标识标牌设计、制作、印刷与安装。",
                "用户需求书",
                "中标人需完成院区导视系统制作和宣传印刷。",
            ]
        )
        clauses = split_into_clauses(text)
        document = NormalizedDocument(
            source_path="/tmp/sample.txt",
            document_name="sample.txt",
            file_hash="catalog-prompt",
            normalized_text_path="/tmp/sample.txt",
            clause_count=len(clauses),
            clauses=clauses,
        )
        review = ReviewResult(
            document_name="sample.txt",
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp="2026-03-16T00:00:00+00:00",
            overall_risk_summary="summary",
            findings=[],
            items_for_human_review=[],
            review_limitations=[],
        )
        classification = classify_procurement_catalog(document)
        prompt = _build_task_prompt(
            task_name="document_audit",
            instruction="测试",
            document=document,
            clauses=clauses[:2],
            review=review,
            classification=classification,
        )
        self.assertIn("主品目更接近", prompt)
        self.assertIn("官方品目映射", prompt)
        if classification.secondary_catalog_names:
            self.assertIn("次品目候选", prompt)


if __name__ == "__main__":
    unittest.main()
