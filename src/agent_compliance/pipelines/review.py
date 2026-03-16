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
            "当前离线执行引擎已接入本地引用资料检索；如未显式启用本地模型，则模板错贴、评分结构和商务链路仍以规则与启发式为主。",
            "当前 section_path 与 table_or_item_label 仍基于启发式识别，对复杂表格和跨页结构的定位仍需继续增强。",
            "当前 page_hint 在缺少显式分页标记时会回退为估算页号，正式审查前仍建议结合原文件复核。",
        ],
    )


def _risk_level(severity_score: int) -> str:
    return {0: "none", 1: "low", 2: "medium", 3: "high"}.get(severity_score, "medium")


def _judgment(issue_type: str, severity_score: int) -> str:
    if issue_type in {"narrow_technical_parameter", "technical_justification_needed"}:
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
        "geographic_restriction": "这类要求会直接压缩非本地供应商的可参与范围。",
        "personnel_restriction": "这类画像限制通常不能直接替代岗位能力和履约经验要求。",
        "excessive_supplier_qualification": "这类条件通常会把与履约无直接关系的企业属性、规模或年限要求变成准入门槛。",
        "irrelevant_certification_or_award": "这类企业称号、荣誉或认证通常不能直接替代项目履约能力判断。",
        "duplicative_scoring_advantage": "如果资格证明材料或与履约弱相关的因素再次计分，容易扭曲竞争。",
        "excessive_scoring_weight": "单一因素分值过高时，容易使评分结构失衡并对少数供应商形成明显倾斜。",
        "post_award_proof_substitution": "允许中标后补证会削弱投标时点评分依据的真实性和可比性。",
        "ambiguous_requirement": "评分分档缺乏量化锚点时，评委之间的尺度容易失衡。",
        "narrow_technical_parameter": "如缺少市场调研和必要性说明，容易形成对少数产品体系的实质偏向。",
        "technical_justification_needed": "此类要求不当然违规，但应补充场景必要性、标准依据和市场可竞争性说明。",
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
        "geographic_restriction": "资格或评分要求存在属地限制",
        "personnel_restriction": "人员条件存在不当画像限制",
        "excessive_supplier_qualification": "资格条件设置与履约关联不足",
        "irrelevant_certification_or_award": "评分中设置与履约弱相关的荣誉资质加分",
        "duplicative_scoring_advantage": "评分中重复放大资格证明材料",
        "excessive_scoring_weight": "单一评分因素权重设置过高",
        "scoring_structure_imbalance": "评分结构中多类高分因素集中出现",
        "post_award_proof_substitution": "评分证明材料允许中标后补证",
        "ambiguous_requirement": "评分分档缺少明确量化锚点",
        "narrow_technical_parameter": "技术参数组合存在定向或过窄风险",
        "technical_justification_needed": "技术要求可能合理但需补充必要性论证",
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
        "geographic_restriction": "可能直接排除非本地供应商，削弱公平竞争。",
        "personnel_restriction": "可能把与履约无直接关系的人员画像条件转化为准入或评分优势。",
        "excessive_supplier_qualification": "可能直接缩小合格供应商范围，降低竞争充分性。",
        "irrelevant_certification_or_award": "可能把综合声誉或企业形象替代为履约能力评价，形成不合理倾斜。",
        "duplicative_scoring_advantage": "可能把本应止于资格审查的因素重复放大为评分优势。",
        "excessive_scoring_weight": "可能导致评分结构明显失衡，过度放大单一因素对中标结果的影响。",
        "scoring_structure_imbalance": "可能导致评分表整体失衡，使少数高分因素对中标结果形成决定性影响。",
        "post_award_proof_substitution": "可能导致评分依据失真，破坏投标文件在截止时点的可比性。",
        "ambiguous_requirement": "可能导致评审尺度不一致、自由裁量过大和复核难度上升。",
        "narrow_technical_parameter": "可能压缩可竞争的品牌和型号范围，并提高投诉风险。",
        "technical_justification_needed": "可能形成较高履约门槛或缩窄供应范围，需结合场景必要性进一步复核。",
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
    if issue_type in {"narrow_technical_parameter", "technical_justification_needed", "other"} and severity_score >= 2:
        return "medium"
    return "high" if severity_score >= 2 else "medium"


def _needs_human_review(issue_type: str) -> bool:
    return issue_type in {
        "narrow_technical_parameter",
        "technical_justification_needed",
        "one_sided_commercial_term",
        "payment_acceptance_linkage",
        "other",
    }


def _human_review_reason(issue_type: str) -> str | None:
    reasons = {
        "narrow_technical_parameter": "需结合市场调研、兼容性边界和临床必要性判断参数是否具有正当性。",
        "technical_justification_needed": "需结合采购场景、适用标准、院感或安全要求及市场调研判断该技术要求是否应保留。",
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

    refined = _merge_sample_scoring_findings(refined)
    refined = _add_scoring_structure_finding(refined)
    refined = _merge_technical_justification_findings(refined)
    refined = _filter_technical_justification_noise(refined)
    refined = _merge_similar_technical_findings(refined)
    refined = _merge_nearby_liability_findings(refined)
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


def _filter_technical_justification_noise(findings: list[Finding]) -> list[Finding]:
    filtered: list[Finding] = []
    for finding in findings:
        if finding.issue_type != "technical_justification_needed":
            filtered.append(finding)
            continue
        normalized = (finding.source_text or "").strip()
        if len(normalized) <= 12:
            continue
        if any(
            marker in normalized
            for marker in (
                "政府采购支持本国产品",
                "支持中小企业",
                "监狱企业",
                "残疾人福利性单位",
                "乡村产业振兴",
            )
        ):
            continue
        if normalized in {"抗菌抗病毒卷帘", "阻燃抑菌抗病毒隔帘", "燃抑菌抗病毒"}:
            continue
        filtered.append(finding)
    return filtered


def _merge_technical_justification_findings(findings: list[Finding]) -> list[Finding]:
    merged: list[Finding] = []
    groups: dict[str, Finding] = {}

    for finding in sorted(findings, key=lambda item: (item.text_line_start, item.issue_type, item.section_path or "")):
        if finding.issue_type != "technical_justification_needed":
            merged.append(finding)
            continue
        family = _technical_justification_family_key(finding)
        if family is None:
            merged.append(finding)
            continue
        existing = groups.get(family)
        if existing is None:
            groups[family] = finding
            continue
        if _can_merge_technical_justification(existing, finding):
            _merge_technical_justification_into(existing, finding, family)
            continue
        merged.append(existing)
        groups[family] = finding

    merged.extend(groups.values())
    merged.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return merged


def _can_merge_technical_justification(left: Finding, right: Finding) -> bool:
    left_section = left.section_path or left.source_section or ""
    right_section = right.section_path or right.source_section or ""
    if "技术要求" not in left_section or "技术要求" not in right_section:
        return False
    if left.document_name != right.document_name:
        return False
    return right.text_line_start - left.text_line_end <= 220


def _merge_technical_justification_into(target: Finding, finding: Finding, family: str) -> None:
    target.text_line_start = min(target.text_line_start, finding.text_line_start)
    target.text_line_end = max(target.text_line_end, finding.text_line_end)
    target.page_hint = _merge_page_hint(target.page_hint, finding.page_hint)
    target.source_text = "；".join(
        list(OrderedDict.fromkeys([part for part in [target.source_text, finding.source_text] if part]))
    )
    target.legal_or_policy_basis = _merge_optional_text(
        [target.legal_or_policy_basis, finding.legal_or_policy_basis]
    )
    target.problem_title = _technical_justification_title(family)
    target.why_it_is_risky = (
        "相邻技术条款涉及安全、环保、院感或检测证明等同类要求，建议作为一个风险点统筹论证。"
        "此类要求不当然违规，但应补充场景必要性、标准依据和市场可竞争性说明。"
    )
    target.rewrite_suggestion = (
        "建议对同一技术组的相邻条款统一说明适用场景、标准依据、检测证明形式和市场可竞争性，"
        "能以国家或行业标准表达的尽量避免叠加细化证明形式。"
    )


def _technical_justification_family_key(finding: Finding) -> str | None:
    normalized = _normalized_source_signature(finding.source_text)
    if any(token in normalized for token in ("阻燃", "抗菌", "抗病毒", "防霉", "环保", "致癌染料", "有机锡", "邻苯", "含氯苯酚", "盐雾")):
        return "safety_environment"
    if any(token in normalized for token in ("cma", "cnas", "第三方", "检测报告")):
        return "testing_proof"
    return "technical_justification_general"


def _technical_justification_title(family: str) -> str:
    titles = {
        "safety_environment": "安全环保类技术要求可能合理但需补充必要性论证（相邻条款已合并）",
        "testing_proof": "检测证明形式要求可能合理但需补充必要性论证（相邻条款已合并）",
        "technical_justification_general": "技术要求可能合理但需补充必要性论证（相邻条款已合并）",
    }
    return titles.get(family, "技术要求可能合理但需补充必要性论证（相邻条款已合并）")


def _add_scoring_structure_finding(findings: list[Finding]) -> list[Finding]:
    weighted = [finding for finding in findings if _is_scoring_weight_candidate(finding)]
    categories = OrderedDict()
    for finding in weighted:
        category = _scoring_weight_category(finding)
        if category is None or category in categories:
            continue
        categories[category] = finding

    if len(categories) < 3:
        return findings

    category_list = list(categories.keys())
    source_findings = list(categories.values())
    aggregate = Finding(
        finding_id="F-000",
        document_name=source_findings[0].document_name,
        problem_title="评分结构中多类高分因素集中出现",
        page_hint=_merge_optional_text((finding.page_hint for finding in source_findings), separator=" / "),
        clause_id=source_findings[0].clause_id,
        source_section=source_findings[0].source_section,
        section_path=source_findings[0].section_path,
        table_or_item_label=source_findings[0].table_or_item_label,
        text_line_start=min(finding.text_line_start for finding in source_findings),
        text_line_end=max(finding.text_line_end for finding in source_findings),
        source_text="；".join(finding.source_text for finding in source_findings if finding.source_text),
        issue_type="scoring_structure_imbalance",
        risk_level="high",
        severity_score=3,
        confidence="high",
        compliance_judgment="likely_non_compliant",
        why_it_is_risky=(
            f"评分表中同时对{_format_category_list(category_list)}设置较高分值，容易使结构性高分集中在少数非价格因素上。"
            "当多类高分因素叠加时，个别供应商可凭既有资质和样品优势快速拉开总分，削弱综合评分的平衡性。"
        ),
        impact_on_competition_or_performance="可能导致评分结构整体失衡，使少数高分因素对中标结果形成决定性影响。",
        legal_or_policy_basis=_merge_optional_text(
            (finding.legal_or_policy_basis for finding in source_findings if finding.legal_or_policy_basis)
        ),
        rewrite_suggestion="建议对样品、认证、业绩等非价格因素重新分配权重，压降单类高分项，并将评分拆解为与履约直接相关的多个可核验指标。",
        needs_human_review=False,
        human_review_reason=None,
    )
    return [*findings, aggregate]


def _is_scoring_weight_candidate(finding: Finding) -> bool:
    if finding.issue_type != "excessive_scoring_weight":
        return False
    section_path = finding.section_path or ""
    source_section = finding.source_section or ""
    return "评标信息" in section_path or "评分" in source_section


def _scoring_weight_category(finding: Finding) -> str | None:
    text = f"{finding.problem_title} {finding.source_text} {finding.clause_id}"
    if any(marker in text for marker in ("样品", "评审为优加", "评审为良加", "评审为中加")):
        return "样品"
    if any(marker in text for marker in ("体系认证", "质量管理体系认证", "职业健康安全管理体系认证", "环境管理体系认证")):
        return "认证"
    if "业绩" in text:
        return "业绩"
    return None


def _format_category_list(categories: list[str]) -> str:
    if len(categories) == 1:
        return categories[0]
    if len(categories) == 2:
        return f"{categories[0]}和{categories[1]}"
    return "、".join(categories[:-1]) + f"和{categories[-1]}"


def _merge_sample_scoring_findings(findings: list[Finding]) -> list[Finding]:
    merged: list[Finding] = []
    pending: list[Finding] = []

    def flush_pending() -> None:
        if not pending:
            return
        if len(pending) == 1:
            merged.append(pending[0])
        else:
            merged.append(_build_sample_scoring_finding(pending))
        pending.clear()

    for finding in sorted(findings, key=lambda item: (item.text_line_start, item.text_line_end, item.issue_type)):
        if _is_sample_scoring_candidate(finding):
            if pending and not _can_merge_sample_scoring(pending[-1], finding):
                flush_pending()
            pending.append(finding)
            continue
        flush_pending()
        merged.append(finding)

    flush_pending()
    merged.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return merged


def _is_sample_scoring_candidate(finding: Finding) -> bool:
    if finding.issue_type not in {"ambiguous_requirement", "excessive_scoring_weight"}:
        return False
    sample_markers = ("评审为优加", "评审为良加", "评审为中加", "评审为差不加分")
    source_text = finding.source_text or ""
    clause_id = finding.clause_id or ""
    return any(marker in source_text or marker in clause_id for marker in sample_markers)


def _can_merge_sample_scoring(left: Finding, right: Finding) -> bool:
    if left.section_path != right.section_path:
        return False
    return right.text_line_start - left.text_line_end <= 2


def _build_sample_scoring_finding(candidates: list[Finding]) -> Finding:
    ordered = sorted(candidates, key=lambda item: (item.text_line_start, item.text_line_end, item.issue_type))
    base = next((item for item in ordered if item.issue_type == "excessive_scoring_weight"), ordered[0])
    merged = Finding(**base.to_dict())
    merged.text_line_start = min(item.text_line_start for item in ordered)
    merged.text_line_end = max(item.text_line_end for item in ordered)
    merged.page_hint = _merge_optional_text((item.page_hint for item in ordered))
    merged.section_path = _merge_optional_text((item.section_path for item in ordered), separator=" / ")
    merged.source_text = "；".join(list(OrderedDict.fromkeys(item.source_text for item in ordered if item.source_text)))
    merged.problem_title = "样品评分主观性强且分值过高（同一评分项已合并）"
    merged.issue_type = "excessive_scoring_weight"
    merged.risk_level = "medium"
    merged.severity_score = 2
    merged.confidence = "high"
    merged.compliance_judgment = "potentially_problematic"
    merged.why_it_is_risky = (
        "样品评分同时采用“优/良/中/差”等主观分档，并设置较高分值，容易让感观判断对总分产生过强影响。"
        "当主观分档缺少量化锚点且分值偏高时，评审自由裁量和评分结构失衡风险都会上升。"
    )
    merged.impact_on_competition_or_performance = "可能过度放大样品感观判断对中标结果的影响，并增加评委尺度不一致风险。"
    merged.legal_or_policy_basis = _merge_optional_text(
        item.legal_or_policy_basis for item in ordered if item.legal_or_policy_basis
    )
    merged.rewrite_suggestion = (
        "建议将样品评分改为按尺寸、材质、做工、阻燃等可核验指标分项评分，并显著降低单项主观分值。"
    )
    merged.needs_human_review = False
    merged.human_review_reason = None
    return merged


def _merge_nearby_liability_findings(findings: list[Finding]) -> list[Finding]:
    others = [finding for finding in findings if finding.issue_type != "one_sided_commercial_term"]
    liabilities = sorted(
        (finding for finding in findings if finding.issue_type == "one_sided_commercial_term"),
        key=lambda item: (item.text_line_start, item.text_line_end, item.section_path or ""),
    )
    if not liabilities:
        return findings

    merged_liabilities: list[Finding] = []
    pending = liabilities[0]
    for finding in liabilities[1:]:
        if _can_merge_liability_finding(pending, finding):
            _merge_liability_finding_into(pending, finding)
            continue
        merged_liabilities.append(pending)
        pending = finding
    merged_liabilities.append(pending)

    merged = [*others, *merged_liabilities]
    merged.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return merged


def _can_merge_liability_finding(left: Finding, right: Finding) -> bool:
    if left.section_path != right.section_path:
        return False
    return right.text_line_start - left.text_line_end <= 6


def _merge_liability_finding_into(target: Finding, finding: Finding) -> None:
    target.text_line_start = min(target.text_line_start, finding.text_line_start)
    target.text_line_end = max(target.text_line_end, finding.text_line_end)
    target.page_hint = _merge_page_hint(target.page_hint, finding.page_hint)
    target.source_text = "；".join(
        list(OrderedDict.fromkeys([part for part in [target.source_text, finding.source_text] if part]))
    )
    target.legal_or_policy_basis = _merge_optional_text(
        [target.legal_or_policy_basis, finding.legal_or_policy_basis]
    )
    target.rewrite_suggestion = (
        "建议对同一风险点下的相邻条款统一改写：按过错和责任来源划分责任，"
        "删除“采购人不承担任何责任”“一切事故全部由供应商承担”等绝对化表述。"
    )
    if "相邻条款已合并" not in target.problem_title:
        target.problem_title = "商务条款存在单方风险转嫁（相邻条款已合并）"
    target.why_it_is_risky = (
        "相邻条款存在同类问题，建议作为一个风险点统筹修改。"
        "条款采用绝对免责或无限扩大供应商责任的表述，容易造成合同权利义务明显失衡。"
        "将付款、责任或验收风险过度转嫁给供应商，容易造成合同权利义务失衡。"
    )


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


def _merge_optional_text(values, separator: str = "；") -> str | None:
    merged = [value for value in OrderedDict.fromkeys(value for value in values if value)]
    if not merged:
        return None
    return separator.join(merged)


def _clip_excerpt(text: str, *, limit: int = 60) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
