from __future__ import annotations

from agent_compliance.schemas import Finding, NormalizedDocument, ReviewResult, RuleHit, utc_now_iso


def build_review_result(document: NormalizedDocument, hits: list[RuleHit]) -> ReviewResult:
    findings: list[Finding] = []
    for index, hit in enumerate(hits, start=1):
        finding = Finding(
            finding_id=f"F-{index:03d}",
            document_name=document.document_name,
            clause_id=hit.matched_clause_id,
            source_section="待按章节路径细化",
            section_path=_find_section(document, hit),
            text_line_start=hit.line_start,
            text_line_end=hit.line_end,
            source_text=hit.matched_text,
            issue_type=hit.issue_type_candidate,
            risk_level=_risk_level(hit.severity_score),
            severity_score=hit.severity_score,
            confidence="medium" if hit.severity_score < 3 else "high",
            compliance_judgment=_judgment(hit.issue_type_candidate, hit.severity_score),
            why_it_is_risky=hit.rationale,
            impact_on_competition_or_performance="可能压缩竞争范围、放大评审自由裁量，或增加履约争议风险。",
            legal_or_policy_basis=None,
            rewrite_suggestion="第一阶段骨架仅输出规则命中结果；后续接入知识检索和本地模型后补全改写建议。",
            needs_human_review=hit.issue_type_candidate in {"narrow_technical_parameter", "one_sided_commercial_term"},
            human_review_reason="第一阶段骨架阶段，涉及兼容性、资金支付和责任边界的条款建议人工复核。"
            if hit.issue_type_candidate in {"narrow_technical_parameter", "one_sided_commercial_term"}
            else None,
        )
        findings.append(finding)

    return ReviewResult(
        document_name=document.document_name,
        review_scope="资格条件、评分规则、技术要求、商务及验收条款",
        jurisdiction="中国",
        review_timestamp=utc_now_iso(),
        overall_risk_summary=f"第一阶段本地审查骨架共命中 {len(findings)} 条规则，当前结果为规则初筛产物，适合作为后续检索和模型判断的输入。",
        findings=findings,
        items_for_human_review=[
            "第一阶段骨架结果仅覆盖规则初筛，复杂条款仍需后续检索层和判断层补强。"
        ],
        review_limitations=[
            "当前为本地执行骨架第一阶段，尚未接入完整法规检索、案例映射和本地大模型改写。",
            "当前 section_path 和 legal_or_policy_basis 仍为基础占位能力，后续版本将进一步细化。",
        ],
    )


def _risk_level(severity_score: int) -> str:
    return {0: "none", 1: "low", 2: "medium", 3: "high"}.get(severity_score, "medium")


def _judgment(issue_type: str, severity_score: int) -> str:
    if issue_type == "narrow_technical_parameter":
        return "needs_human_review"
    if severity_score >= 3:
        return "likely_non_compliant"
    if severity_score == 2:
        return "potentially_problematic"
    return "likely_compliant"


def _find_section(document: NormalizedDocument, hit: RuleHit) -> str | None:
    for clause in document.clauses:
        if clause.line_start == hit.line_start:
            return clause.section_path
    return None
