from __future__ import annotations

import os
import unittest

from agent_compliance.cli import build_parser
from agent_compliance.config import LLMConfig, detect_llm_config
from agent_compliance.pipelines.llm_enhance import _build_prompt, enhance_review_result
from agent_compliance.schemas import Finding, ReviewResult
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


if __name__ == "__main__":
    unittest.main()
