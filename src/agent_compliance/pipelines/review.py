from __future__ import annotations

from collections import OrderedDict

from agent_compliance.knowledge.references_index import ReferenceRecord, find_references
from agent_compliance.schemas import Finding, NormalizedDocument, ReviewResult, RuleHit, utc_now_iso


def build_review_result(document: NormalizedDocument, hits: list[RuleHit]) -> ReviewResult:
    deduped_hits = _dedupe_hits(hits)
    findings: list[Finding] = []
    for index, hit in enumerate(deduped_hits, start=1):
        clause = _find_clause(document, hit)
        references = find_references(
            reference_ids=hit.related_reference_ids,
            rule_ids=hit.related_rule_ids,
            issue_type=hit.issue_type_candidate,
        )
        finding = Finding(
            finding_id=f"F-{index:03d}",
            document_name=document.document_name,
            page_hint=clause.page_hint if clause else None,
            clause_id=hit.matched_clause_id,
            source_section=clause.source_section if clause and clause.source_section else hit.source_section,
            section_path=clause.section_path if clause else hit.source_section,
            table_or_item_label=clause.table_or_item_label if clause else None,
            text_line_start=hit.line_start,
            text_line_end=hit.line_end,
            source_text=hit.matched_text,
            issue_type=hit.issue_type_candidate,
            risk_level=_risk_level(hit.severity_score),
            severity_score=hit.severity_score,
            confidence=_confidence(hit.issue_type_candidate, hit.severity_score),
            compliance_judgment=_judgment(hit.issue_type_candidate, hit.severity_score),
            why_it_is_risky=_expand_rationale(hit),
            impact_on_competition_or_performance=_impact_text(hit.issue_type_candidate),
            legal_or_policy_basis=_legal_basis_text(references),
            rewrite_suggestion=hit.rewrite_hint,
            needs_human_review=_needs_human_review(hit.issue_type_candidate),
            human_review_reason=_human_review_reason(hit.issue_type_candidate),
        )
        findings.append(finding)

    return ReviewResult(
        document_name=document.document_name,
        review_scope="资格条件、评分规则、技术要求、商务及验收条款",
        jurisdiction="中国",
        review_timestamp=utc_now_iso(),
        overall_risk_summary=_overall_summary(findings),
        findings=findings,
        items_for_human_review=_human_review_items(findings),
        review_limitations=[
            "当前为第二阶段离线骨架，已接入本地引用资料检索，但尚未接入本地大模型做边界判断和改写增强。",
            "当前 section_path 仍基于启发式章节识别，对复杂表格和跨页结构的定位仍需继续增强。",
        ],
    )


def _risk_level(severity_score: int) -> str:
    return {0: "none", 1: "low", 2: "medium", 3: "high"}.get(severity_score, "medium")


def _judgment(issue_type: str, severity_score: int) -> str:
    if issue_type in {"narrow_technical_parameter"}:
        return "needs_human_review"
    if issue_type == "one_sided_commercial_term" and severity_score >= 3:
        return "potentially_problematic"
    if severity_score >= 3:
        return "likely_non_compliant"
    if severity_score == 2:
        return "potentially_problematic"
    return "likely_compliant"


def _find_section(document: NormalizedDocument, hit: RuleHit) -> str | None:
    clause = _find_clause(document, hit)
    return clause.section_path if clause else None


def _find_clause(document: NormalizedDocument, hit: RuleHit):
    for clause in document.clauses:
        if clause.line_start == hit.line_start and clause.text == hit.matched_text:
            return clause
    for clause in document.clauses:
        if clause.line_start == hit.line_start:
            return clause
    return None


def _dedupe_hits(hits: list[RuleHit]) -> list[RuleHit]:
    unique: "OrderedDict[tuple[int, str], RuleHit]" = OrderedDict()
    for hit in hits:
        key = (hit.line_start, hit.issue_type_candidate)
        existing = unique.get(key)
        if existing is None or hit.severity_score > existing.severity_score:
            unique[key] = hit
    return list(unique.values())


def _expand_rationale(hit: RuleHit) -> str:
    suffix = {
        "excessive_supplier_qualification": "这类条件通常会把与履约无直接关系的企业属性、规模或年限要求变成准入门槛。",
        "irrelevant_certification_or_award": "这类企业称号、荣誉或认证通常不能直接替代项目履约能力判断。",
        "duplicative_scoring_advantage": "如果资格证明材料或与履约弱相关的因素再次计分，容易扭曲竞争。",
        "ambiguous_requirement": "评分分档缺乏量化锚点时，评委之间的尺度容易失衡。",
        "narrow_technical_parameter": "如缺少市场调研和必要性说明，容易形成对少数产品体系的实质偏向。",
        "unclear_acceptance_standard": "验收清单、触发条件和费用边界不清时，后续履约争议风险会升高。",
        "one_sided_commercial_term": "将付款、责任或验收风险过度转嫁给供应商，容易造成合同权利义务失衡。",
        "other": "这类条款通常需要进一步判断是否超出采购标的实际需要或属于模板残留。",
    }
    return f"{hit.rationale}{suffix.get(hit.issue_type_candidate, '')}"


def _impact_text(issue_type: str) -> str:
    mapping = {
        "excessive_supplier_qualification": "可能直接缩小合格供应商范围，降低竞争充分性。",
        "irrelevant_certification_or_award": "可能把综合声誉或企业形象替代为履约能力评价，形成不合理倾斜。",
        "duplicative_scoring_advantage": "可能把本应止于资格审查的因素重复放大为评分优势。",
        "ambiguous_requirement": "可能导致评审尺度不一致、自由裁量过大和复核难度上升。",
        "narrow_technical_parameter": "可能压缩可竞争的品牌和型号范围，并提高投诉风险。",
        "unclear_acceptance_standard": "可能导致验收标准不稳定、成本难估算和后续争议升级。",
        "one_sided_commercial_term": "可能抬高供应商报价和履约风险，增加合同争议概率。",
        "other": "可能扩张供应商义务范围或引入与项目不直接相关的履约成本。",
    }
    return mapping.get(issue_type, "可能影响公平竞争、履约可执行性或复核稳定性。")


def _legal_basis_text(references: list[ReferenceRecord]) -> str | None:
    if not references:
        return None
    snippets = []
    for record in references:
        if record.source_org:
            snippets.append(f"{record.title}（{record.source_org}）")
        else:
            snippets.append(record.title)
    return "；".join(snippets[:3])


def _confidence(issue_type: str, severity_score: int) -> str:
    if issue_type in {"narrow_technical_parameter", "other"} and severity_score >= 2:
        return "medium"
    return "high" if severity_score >= 2 else "medium"


def _needs_human_review(issue_type: str) -> bool:
    return issue_type in {"narrow_technical_parameter", "one_sided_commercial_term", "other"}


def _human_review_reason(issue_type: str) -> str | None:
    reasons = {
        "narrow_technical_parameter": "需结合市场调研、兼容性边界和临床必要性判断参数是否具有正当性。",
        "one_sided_commercial_term": "需结合采购人内控、财政支付流程和合同谈判边界判断条款是否可保留。",
        "other": "需结合项目背景判断该义务是否属于模板残留或确有政策和业务必要性。",
    }
    return reasons.get(issue_type)


def _overall_summary(findings: list[Finding]) -> str:
    high = sum(1 for finding in findings if finding.risk_level == "high")
    medium = sum(1 for finding in findings if finding.risk_level == "medium")
    return (
        f"本地离线审查共形成 {len(findings)} 条去重 findings，其中高风险 {high} 条、中风险 {medium} 条。"
        " 当前结果已接入本地规则映射和引用资料检索，可作为正式审查前的离线初筛与复审输入。"
    )


def _human_review_items(findings: list[Finding]) -> list[str]:
    items = []
    for finding in findings:
        if finding.needs_human_review and finding.human_review_reason:
            items.append(f"{finding.finding_id}：{finding.human_review_reason}")
    return items
