from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from agent_compliance.knowledge.references_index import ReferenceRecord, find_references
from agent_compliance.schemas import Finding, NormalizedDocument, ReviewResult, RuleHit, utc_now_iso


def build_review_result(document: NormalizedDocument, hits: list[RuleHit]) -> ReviewResult:
    grouped_hits = _group_hits(document, _dedupe_hits(hits))
    findings: list[Finding] = []
    for index, group in enumerate(grouped_hits, start=1):
        hit = group.primary_hit
        clause = _find_clause(document, hit)
        references = find_references(
            reference_ids=group.reference_ids,
            rule_ids=group.rule_ids,
            issue_type=hit.issue_type_candidate,
        )
        finding = Finding(
            finding_id=f"F-{index:03d}",
            document_name=document.document_name,
            problem_title=_problem_title(group, clause),
            page_hint=clause.page_hint if clause else None,
            clause_id=hit.matched_clause_id,
            source_section=clause.source_section if clause and clause.source_section else hit.source_section,
            section_path=clause.section_path if clause else hit.source_section,
            table_or_item_label=clause.table_or_item_label if clause else None,
            text_line_start=group.line_start,
            text_line_end=group.line_end,
            source_text=group.source_text,
            issue_type=hit.issue_type_candidate,
            risk_level=_risk_level(hit.severity_score),
            severity_score=hit.severity_score,
            confidence=_confidence(hit.issue_type_candidate, hit.severity_score),
            compliance_judgment=_judgment(hit.issue_type_candidate, hit.severity_score),
            why_it_is_risky=_expand_rationale(group),
            impact_on_competition_or_performance=_impact_text(hit.issue_type_candidate),
            legal_or_policy_basis=_legal_basis_text(references),
            rewrite_suggestion=_rewrite_suggestion(group),
            needs_human_review=_needs_human_review(hit.issue_type_candidate),
            human_review_reason=_human_review_reason(hit.issue_type_candidate),
        )
        findings.append(finding)

    findings = _refine_findings(findings)
    findings = _renumber_findings(findings)

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
            "当前 section_path 与 table_or_item_label 仍基于启发式识别，对复杂表格和跨页结构的定位仍需继续增强。",
            "当前 page_hint 在缺少显式分页标记时会回退为估算页号，正式审查前仍建议结合原文件复核。",
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
        key = (hit.line_start, hit.merge_key)
        existing = unique.get(key)
        if existing is None or hit.severity_score > existing.severity_score:
            unique[key] = hit
    return list(unique.values())


@dataclass
class HitGroup:
    primary_hit: RuleHit
    hits: list[RuleHit]
    section_path: str | None
    line_start: int
    line_end: int
    source_text: str
    rule_ids: tuple[str, ...]
    reference_ids: tuple[str, ...]


def _group_hits(document: NormalizedDocument, hits: list[RuleHit]) -> list[HitGroup]:
    groups: list[HitGroup] = []
    sorted_hits = sorted(hits, key=lambda item: (item.line_start, item.line_end, item.rule_id))
    for hit in sorted_hits:
        clause = _find_clause(document, hit)
        if groups and _should_merge(groups[-1], hit, clause):
            groups[-1] = _merge_group(groups[-1], hit)
            continue
        groups.append(
            HitGroup(
                primary_hit=hit,
                hits=[hit],
                section_path=clause.section_path if clause else hit.source_section,
                line_start=hit.line_start,
                line_end=hit.line_end,
                source_text=hit.matched_text,
                rule_ids=hit.related_rule_ids,
                reference_ids=hit.related_reference_ids,
            )
        )
    return groups


def _should_merge(group: HitGroup, hit: RuleHit, clause) -> bool:
    primary = group.primary_hit
    if primary.merge_key != hit.merge_key:
        return False
    if hit.line_start - group.line_end > 3:
        return False
    if clause is None:
        return False
    return group.section_path == clause.section_path


def _merge_group(group: HitGroup, hit: RuleHit) -> HitGroup:
    hits = [*group.hits, hit]
    primary_hit = max(hits, key=lambda item: (item.severity_score, -item.line_start))
    source_texts = list(OrderedDict.fromkeys(item.matched_text for item in hits))
    return HitGroup(
        primary_hit=primary_hit,
        hits=hits,
        section_path=group.section_path,
        line_start=min(item.line_start for item in hits),
        line_end=max(item.line_end for item in hits),
        source_text="；".join(source_texts[:3]),
        rule_ids=_merge_tuple_values(item.related_rule_ids for item in hits),
        reference_ids=_merge_tuple_values(item.related_reference_ids for item in hits),
    )


def _merge_tuple_values(values) -> tuple[str, ...]:
    merged: list[str] = []
    for group in values:
        for item in group:
            if item not in merged:
                merged.append(item)
    return tuple(merged)


def _expand_rationale(group: HitGroup) -> str:
    hit = group.primary_hit
    suffix = {
        "excessive_supplier_qualification": "这类条件通常会把与履约无直接关系的企业属性、规模或年限要求变成准入门槛。",
        "irrelevant_certification_or_award": "这类企业称号、荣誉或认证通常不能直接替代项目履约能力判断。",
        "duplicative_scoring_advantage": "如果资格证明材料或与履约弱相关的因素再次计分，容易扭曲竞争。",
        "excessive_scoring_weight": "单一因素分值过高时，容易使评分结构失衡并对少数供应商形成明显倾斜。",
        "post_award_proof_substitution": "允许中标后补证会削弱投标时点评分依据的真实性和可比性。",
        "ambiguous_requirement": "评分分档缺乏量化锚点时，评委之间的尺度容易失衡。",
        "narrow_technical_parameter": "如缺少市场调研和必要性说明，容易形成对少数产品体系的实质偏向。",
        "unclear_acceptance_standard": "验收清单、触发条件和费用边界不清时，后续履约争议风险会升高。",
        "one_sided_commercial_term": "将付款、责任或验收风险过度转嫁给供应商，容易造成合同权利义务失衡。",
        "payment_acceptance_linkage": "当抽检、终验和付款深度绑定时，供应商回款预期和履约成本都更难稳定评估。",
        "other": "这类条款通常需要进一步判断是否超出采购标的实际需要或属于模板残留。",
    }
    prefix = "相邻条款存在同类问题，建议作为一个风险点统筹修改。" if len(group.hits) > 1 else ""
    return f"{prefix}{hit.rationale}{suffix.get(hit.issue_type_candidate, '')}"


def _rewrite_suggestion(group: HitGroup) -> str:
    hints = list(OrderedDict.fromkeys(hit.rewrite_hint for hit in group.hits if hit.rewrite_hint))
    if len(group.hits) > 1 and hints:
        return f"建议对同一风险点下的相邻条款统一改写：{'；'.join(hints[:2])}"
    return "；".join(hints[:2]) if hints else group.primary_hit.rewrite_hint


def _problem_title(group: HitGroup, clause) -> str:
    issue = group.primary_hit.issue_type_candidate
    titles = {
        "excessive_supplier_qualification": "资格条件设置与履约关联不足",
        "irrelevant_certification_or_award": "评分中设置与履约弱相关的荣誉资质加分",
        "duplicative_scoring_advantage": "评分中重复放大资格证明材料",
        "excessive_scoring_weight": "单一评分因素权重设置过高",
        "post_award_proof_substitution": "评分证明材料允许中标后补证",
        "ambiguous_requirement": "评分分档缺少明确量化锚点",
        "narrow_technical_parameter": "技术参数组合存在定向或过窄风险",
        "unclear_acceptance_standard": "验收标准或检测边界不清",
        "one_sided_commercial_term": "商务条款存在单方风险转嫁",
        "payment_acceptance_linkage": "付款条件与抽检终验深度绑定",
        "other": "条款内容可能存在模板残留或义务外扩",
    }
    base = titles.get(issue, "条款存在合规风险")
    if len(group.hits) > 1:
        if clause and clause.section_path and "评标信息" in clause.section_path:
            return f"{base}（同一评分项已合并）"
        return f"{base}（相邻条款已合并）"
    return base


def _impact_text(issue_type: str) -> str:
    mapping = {
        "excessive_supplier_qualification": "可能直接缩小合格供应商范围，降低竞争充分性。",
        "irrelevant_certification_or_award": "可能把综合声誉或企业形象替代为履约能力评价，形成不合理倾斜。",
        "duplicative_scoring_advantage": "可能把本应止于资格审查的因素重复放大为评分优势。",
        "excessive_scoring_weight": "可能导致评分结构明显失衡，过度放大单一因素对中标结果的影响。",
        "post_award_proof_substitution": "可能导致评分依据失真，破坏投标文件在截止时点的可比性。",
        "ambiguous_requirement": "可能导致评审尺度不一致、自由裁量过大和复核难度上升。",
        "narrow_technical_parameter": "可能压缩可竞争的品牌和型号范围，并提高投诉风险。",
        "unclear_acceptance_standard": "可能导致验收标准不稳定、成本难估算和后续争议升级。",
        "one_sided_commercial_term": "可能抬高供应商报价和履约风险，增加合同争议概率。",
        "payment_acceptance_linkage": "可能导致回款周期不稳定、履约成本难估算和付款争议增多。",
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
    return issue_type in {"narrow_technical_parameter", "one_sided_commercial_term", "payment_acceptance_linkage", "other"}


def _human_review_reason(issue_type: str) -> str | None:
    reasons = {
        "narrow_technical_parameter": "需结合市场调研、兼容性边界和临床必要性判断参数是否具有正当性。",
        "one_sided_commercial_term": "需结合采购人内控、财政支付流程和合同谈判边界判断条款是否可保留。",
        "payment_acceptance_linkage": "需结合抽检机制、终验流程和财政支付安排判断付款节点设置是否合理。",
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


def _refine_findings(findings: list[Finding]) -> list[Finding]:
    refined: list[Finding] = []
    primary_signatures: list[tuple[str, str]] = []
    appendix_findings: list[Finding] = []

    for finding in findings:
        finding.section_path = _shorten_section_path(finding.section_path)
        signature = (finding.issue_type, _normalized_source_signature(finding.source_text))
        if _is_appendix_duplicate_candidate(finding):
            appendix_findings.append(finding)
            continue
        primary_signatures.append(signature)
        refined.append(finding)

    for finding in appendix_findings:
        signature = (finding.issue_type, _normalized_source_signature(finding.source_text))
        if _matches_existing_signature(signature, primary_signatures):
            continue
        refined.append(finding)

    refined = _merge_similar_technical_findings(refined)
    for finding in refined:
        finding.source_text = _representative_excerpt(finding.source_text)
    return refined


def _renumber_findings(findings: list[Finding]) -> list[Finding]:
    for index, finding in enumerate(findings, start=1):
        finding.finding_id = f"F-{index:03d}"
    return findings


def _shorten_section_path(section_path: str | None) -> str | None:
    if not section_path:
        return None
    parts = [part.strip() for part in section_path.split("-") if part.strip()]
    shortened = [_shorten_segment(part) for part in parts]
    return "-".join(shortened)


def _shorten_segment(segment: str) -> str:
    if len(segment) <= 36:
        return segment
    return f"{segment[:30]}..."


def _normalized_source_signature(source_text: str) -> str:
    normalized = "".join(ch for ch in source_text if ch.isalnum())
    return normalized[:80]


def _is_appendix_duplicate_candidate(finding: Finding) -> bool:
    return bool(finding.section_path and "第四章 投标文件组成要求及格式" in finding.section_path)


def _matches_existing_signature(
    candidate: tuple[str, str], primary_signatures: list[tuple[str, str]]
) -> bool:
    candidate_issue, candidate_text = candidate
    for issue_type, primary_text in primary_signatures:
        if issue_type != candidate_issue:
            continue
        if candidate_text == primary_text:
            return True
        if candidate_text and primary_text and (candidate_text in primary_text or primary_text in candidate_text):
            return True
    return False


def _merge_similar_technical_findings(findings: list[Finding]) -> list[Finding]:
    merged: list[Finding] = []
    tech_groups: dict[str, Finding] = {}

    for finding in findings:
        if finding.issue_type != "narrow_technical_parameter":
            merged.append(finding)
            continue
        family = _technical_family_key(finding.source_text)
        if family is None:
            merged.append(finding)
            continue
        existing = tech_groups.get(family)
        if existing is None:
            tech_groups[family] = finding
            continue
        _merge_finding_into(existing, finding, family)

    merged.extend(tech_groups.values())
    merged.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return merged


def _technical_family_key(source_text: str) -> str | None:
    normalized = _normalized_source_signature(source_text)
    if "无线插拔技术无线连接技术" in normalized:
        return "wireless_connection"
    if "工作频率12MHz20MHz支持两个频率一键切换" in normalized:
        return "ultrasound_frequency"
    if "兼容高清电子胃肠镜" in normalized:
        return "compatibility"
    if "探头外径" in normalized:
        return "probe_diameter"
    return None


def _merge_finding_into(target: Finding, finding: Finding, family: str) -> None:
    target.text_line_start = min(target.text_line_start, finding.text_line_start)
    target.text_line_end = max(target.text_line_end, finding.text_line_end)
    target.page_hint = _merge_page_hint(target.page_hint, finding.page_hint)
    target.source_text = "；".join(
        list(OrderedDict.fromkeys([part for part in [target.source_text, finding.source_text] if part]))
    )
    target.section_path = _merge_section_path(target.section_path, finding.section_path)
    target.problem_title = _merged_technical_title(family)
    target.why_it_is_risky = "同类技术参数在多个设备章节中重复出现，建议合并评估其必要性和市场兼容范围。" + target.why_it_is_risky
    target.rewrite_suggestion = "建议将同类技术参数统一改为功能效果导向表述，并一次性说明适用设备范围、必要性和兼容边界。"
    target.human_review_reason = "需结合市场调研、兼容性边界、适用设备范围和临床必要性统一判断参数是否具有正当性。"


def _merge_page_hint(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right or left == right:
        return left
    return f"{left} / {right}"


def _merge_section_path(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right or left == right:
        return left
    left_parts = left.split("-")
    right_parts = right.split("-")
    common: list[str] = []
    for l_part, r_part in zip(left_parts, right_parts):
        if l_part == r_part:
            common.append(l_part)
        else:
            break
    suffixes = [left_parts[-1], right_parts[-1]]
    merged_suffix = " / ".join(list(OrderedDict.fromkeys(suffixes)))
    if common:
        return "-".join([*common, merged_suffix])
    return merged_suffix


def _merged_technical_title(family: str) -> str:
    titles = {
        "wireless_connection": "同类无线连接和防水消毒参数在多个设备章节重复出现",
        "ultrasound_frequency": "同类超声频率参数在多个设备章节重复出现",
        "compatibility": "兼容性参数存在定向或过窄风险",
        "probe_diameter": "探头尺寸参数在多个设备章节中较为集中",
    }
    return titles.get(family, "同类技术参数在多个设备章节重复出现")


def _representative_excerpt(source_text: str) -> str:
    parts = [part.strip() for part in source_text.split("；") if part.strip()]
    if not parts:
        return source_text
    normalized_parts = list(OrderedDict.fromkeys(parts))
    snippets = [_clip_excerpt(part) for part in normalized_parts[:2]]
    excerpt = "；".join(snippets)
    if len(normalized_parts) > 2:
        excerpt = f"{excerpt} 等{len(normalized_parts)}项"
    return excerpt


def _clip_excerpt(text: str, *, limit: int = 60) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
