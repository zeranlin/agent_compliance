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

    findings = _drop_false_positive_findings(findings)
    findings = _refine_findings(document, findings)

    return reconcile_review_result(
        ReviewResult(
            document_name=document.document_name,
            review_scope="资格条件、评分规则、技术要求、商务及验收条款",
            jurisdiction="中国",
            review_timestamp=utc_now_iso(),
            overall_risk_summary="",
            findings=findings,
            items_for_human_review=[],
            review_limitations=[
                "当前离线执行引擎已接入本地引用资料检索；如未显式启用本地模型，则模板错贴、评分结构和商务链路仍以规则与启发式为主。",
                "当前 section_path 与 table_or_item_label 仍基于启发式识别，对复杂表格和跨页结构的定位仍需继续增强。",
                "当前 page_hint 在缺少显式分页标记时会回退为估算页号，正式审查前仍建议结合原文件复核。",
            ],
        )
    )


def reconcile_review_result(review: ReviewResult) -> ReviewResult:
    review.findings = _apply_finding_arbiter(review.findings)
    review.findings = _sort_findings(review.findings)
    review.findings = _renumber_findings(review.findings)
    review.overall_risk_summary = _overall_summary(review.findings)
    review.items_for_human_review = _human_review_items(review.findings)
    return review


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


@dataclass
class DocumentRiskProfile:
    dominant_sections: tuple[str, ...]
    dominant_issue_types: tuple[str, ...]
    dominant_theme_titles: tuple[str, ...]
    high_risk_count: int
    medium_risk_count: int


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
        "brand_or_model_designation": "在评分或商务条款中直接按品牌档次赋分，容易把品牌偏好直接转化为竞争优势。",
        "excessive_supplier_qualification": "这类条件通常会把与履约无直接关系的企业属性、规模或年限要求变成准入门槛。",
        "qualification_domain_mismatch": "当资格条件与采购标的所属领域明显不匹配时，往往意味着模板错贴或不当扩大准入门槛。",
        "irrelevant_certification_or_award": "这类企业称号、荣誉或认证通常不能直接替代项目履约能力判断。",
        "duplicative_scoring_advantage": "如果资格证明材料或与履约弱相关的因素再次计分，容易扭曲竞争。",
        "scoring_content_mismatch": "评分项如果混入与评分主题不一致的案例、证书、规模或行业错位内容，容易把不相关材料变成竞争优势。",
        "excessive_scoring_weight": "单一因素分值过高时，容易使评分结构失衡并对少数供应商形成明显倾斜。",
        "post_award_proof_substitution": "允许中标后补证会削弱投标时点评分依据的真实性和可比性。",
        "ambiguous_requirement": "评分分档缺乏量化锚点时，评委之间的尺度容易失衡。",
        "narrow_technical_parameter": "如缺少市场调研和必要性说明，容易形成对少数产品体系的实质偏向。",
        "technical_justification_needed": "此类要求不当然违规，但应补充场景必要性、标准依据、市场可得性和是否存在更中性表达的说明。",
        "unclear_acceptance_standard": "验收清单、触发条件和费用边界不清时，后续履约争议风险会升高。",
        "one_sided_commercial_term": "将付款、责任或验收风险过度转嫁给供应商，容易造成合同权利义务失衡。",
        "payment_acceptance_linkage": "当抽检、终验和付款深度绑定时，供应商回款预期和履约成本都更难稳定评估。",
        "template_mismatch": "这类条款通常表现为跨领域模板残留、开放式义务外扩或与标的不直接相关的履约要求。",
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
    combined_text = f"{group.source_text} {group.primary_hit.matched_clause_id}"
    if issue == "geographic_restriction" and any(
        marker in combined_text for marker in ("1小时", "60分钟", "1.5小时", "90分钟", "到达现场")
    ):
        base = "售后响应时限设置形成事实上的属地倾斜"
        if len(group.hits) > 1:
            return f"{base}（同一评分项已合并）"
        return base
    titles = {
        "geographic_restriction": "资格或评分要求存在属地限制",
        "personnel_restriction": "人员条件存在不当画像限制",
        "brand_or_model_designation": "评分或条款中存在品牌倾向",
        "excessive_supplier_qualification": "资格条件设置与履约关联不足",
        "qualification_domain_mismatch": "资格条件中出现与采购标的不匹配的资质要求",
        "irrelevant_certification_or_award": "评分中设置与履约弱相关的荣誉资质加分",
        "duplicative_scoring_advantage": "评分中重复放大资格证明材料",
        "scoring_content_mismatch": "评分内容与评分主题或采购标的不完全匹配",
        "excessive_scoring_weight": "单一评分因素权重设置过高",
        "scoring_structure_imbalance": "评分结构中多类高分因素集中出现",
        "post_award_proof_substitution": "评分证明材料允许中标后补证",
        "ambiguous_requirement": "评分分档缺少明确量化锚点",
        "narrow_technical_parameter": "技术参数组合存在定向或过窄风险",
        "technical_justification_needed": "技术要求可能合理但需补充必要性论证",
        "unclear_acceptance_standard": "验收标准或检测边界不清",
        "one_sided_commercial_term": "商务条款存在单方风险转嫁",
        "payment_acceptance_linkage": "付款条件与抽检终验深度绑定",
        "template_mismatch": "条款内容可能存在模板错贴或义务外扩",
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
        "brand_or_model_designation": "可能把品牌偏好直接转化为竞争优势，并对其他满足需求的产品形成不合理排斥。",
        "excessive_supplier_qualification": "可能直接缩小合格供应商范围，降低竞争充分性。",
        "qualification_domain_mismatch": "可能把与采购标的不匹配的行业资质、登记或许可错误地变成准入条件。",
        "irrelevant_certification_or_award": "可能把综合声誉或企业形象替代为履约能力评价，形成不合理倾斜。",
        "duplicative_scoring_advantage": "可能把本应止于资格审查的因素重复放大为评分优势。",
        "scoring_content_mismatch": "可能把与评分主题无关或与标的不匹配的材料转化为得分点，扭曲评审重心。",
        "excessive_scoring_weight": "可能导致评分结构明显失衡，过度放大单一因素对中标结果的影响。",
        "scoring_structure_imbalance": "可能导致评分表整体失衡，使少数高分因素对中标结果形成决定性影响。",
        "post_award_proof_substitution": "可能导致评分依据失真，破坏投标文件在截止时点的可比性。",
        "ambiguous_requirement": "可能导致评审尺度不一致、自由裁量过大和复核难度上升。",
        "narrow_technical_parameter": "可能压缩可竞争的品牌和型号范围，并提高投诉风险。",
        "technical_justification_needed": "可能在形式上缩窄供应范围或提高证明成本，需结合适用场景、标准依据和市场可得性进一步复核。",
        "unclear_acceptance_standard": "可能导致验收标准不稳定、成本难估算和后续争议升级。",
        "one_sided_commercial_term": "可能抬高供应商报价和履约风险，增加合同争议概率。",
        "payment_acceptance_linkage": "可能导致回款周期不稳定、履约成本难估算和付款争议增多。",
        "template_mismatch": "可能扩张供应商义务范围，并将与采购标的不直接相关的履约成本转嫁给中标人。",
        "other": "可能扩张供应商义务范围或引入与项目不直接相关的履约成本。",
    }
    return mapping.get(issue_type, "可能影响公平竞争、履约可执行性或复核稳定性。")


def _drop_false_positive_findings(findings: list[Finding]) -> list[Finding]:
    filtered: list[Finding] = []
    for finding in findings:
        section_path = finding.section_path or ""
        if (
            finding.issue_type == "ambiguous_requirement"
            and any(
                token in section_path
                for token in (
                    "政府采购履约异常情况反馈表",
                    "评审程序及评审方法",
                    "通用条款",
                )
            )
        ):
            continue
        filtered.append(finding)
    return filtered


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
    if issue_type in {"narrow_technical_parameter", "technical_justification_needed", "template_mismatch", "other"} and severity_score >= 2:
        return "medium"
    return "high" if severity_score >= 2 else "medium"


def _needs_human_review(issue_type: str) -> bool:
    return issue_type in {
        "narrow_technical_parameter",
        "technical_justification_needed",
        "one_sided_commercial_term",
        "payment_acceptance_linkage",
        "qualification_domain_mismatch",
        "scoring_content_mismatch",
        "template_mismatch",
        "other",
    }


def _human_review_reason(issue_type: str) -> str | None:
    reasons = {
        "narrow_technical_parameter": "需结合市场调研、兼容性边界和临床必要性判断参数是否具有正当性。",
        "technical_justification_needed": "需结合采购场景、适用标准、市场可得性和是否存在更中性表达判断该技术要求是否应保留。",
        "one_sided_commercial_term": "需结合采购人内控、财政支付流程和合同谈判边界判断条款是否可保留。",
        "payment_acceptance_linkage": "需结合抽检机制、终验流程和财政支付安排判断付款节点设置是否合理。",
        "qualification_domain_mismatch": "需结合采购标的领域、法定许可要求和履约实际判断该资质是否确有必要。",
        "scoring_content_mismatch": "需结合评分主题和项目履约目标判断该评分内容是否与评审事项直接相关。",
        "template_mismatch": "需结合项目范围判断该条款是否属于模板残留、跨领域复制或确有业务必要性。",
        "other": "需结合项目背景判断该义务是否属于模板残留或确有政策和业务必要性。",
    }
    return reasons.get(issue_type)


def _overall_summary(findings: list[Finding]) -> str:
    profile = _build_document_risk_profile(findings)
    high = sum(1 for finding in findings if finding.risk_level == "high")
    medium = sum(1 for finding in findings if finding.risk_level == "medium")
    summary = (
        f"本地离线审查共形成 {len(findings)} 条去重 findings，其中高风险 {high} 条、中风险 {medium} 条。"
        " 当前结果已接入本地规则映射和引用资料检索，可作为正式审查前的离线初筛与复审输入。"
    )
    if profile.dominant_sections:
        summary += f" 该文件的主风险重心集中在{_join_labels(profile.dominant_sections)}。"
    if profile.dominant_theme_titles:
        summary += f" 当前最突出的主问题包括：{_join_labels(profile.dominant_theme_titles)}。"
    return summary


def _build_document_risk_profile(findings: list[Finding]) -> DocumentRiskProfile:
    if not findings:
        return DocumentRiskProfile((), (), (), 0, 0)

    weighted_findings = [finding for finding in findings if finding.risk_level in {"high", "medium"}]
    candidates = weighted_findings or findings

    section_scores: "OrderedDict[str, int]" = OrderedDict()
    issue_scores: "OrderedDict[str, int]" = OrderedDict()
    theme_titles: list[str] = []
    for finding in candidates:
        weight = 2 if finding.risk_level == "high" else 1
        section = _section_key_from_finding(finding)
        section_scores[section] = section_scores.get(section, 0) + weight
        issue_scores[finding.issue_type] = issue_scores.get(finding.issue_type, 0) + weight
        if finding.finding_origin == "analyzer" and finding.problem_title not in theme_titles:
            theme_titles.append(finding.problem_title)

    dominant_sections = tuple(
        _section_label_from_key(section)
        for section, _score in sorted(section_scores.items(), key=lambda item: (-item[1], item[0]))[:3]
    )
    dominant_issue_types = tuple(
        issue_type for issue_type, _score in sorted(issue_scores.items(), key=lambda item: (-item[1], item[0]))[:4]
    )
    dominant_theme_titles = tuple(theme_titles[:3])
    return DocumentRiskProfile(
        dominant_sections=dominant_sections,
        dominant_issue_types=dominant_issue_types,
        dominant_theme_titles=dominant_theme_titles,
        high_risk_count=sum(1 for finding in findings if finding.risk_level == "high"),
        medium_risk_count=sum(1 for finding in findings if finding.risk_level == "medium"),
    )


def _join_labels(values: tuple[str, ...]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]}和{values[1]}"
    return f"{'、'.join(values[:-1])}和{values[-1]}"


def _section_key_from_finding(finding: Finding) -> str:
    semantic_text = " ".join(
        part
        for part in (
            finding.problem_title,
            finding.issue_type,
        )
        if part
    )
    location_text = " ".join(
        part
        for part in (
            finding.section_path or "",
            finding.source_section or "",
        )
        if part
    )
    if any(token in semantic_text for token in ("评分", "演示", "品牌档次", "认证评分", "商务评分", "样品", "scoring_")):
        return "scoring"
    if any(token in semantic_text for token in ("技术", "标准", "检测报告", "证明材料", "参数", "technical_")):
        return "technical"
    if any(
        token in semantic_text
        for token in ("验收", "付款", "责任", "违约", "交货", "模板残留", "义务外扩", "commercial", "acceptance", "payment")
    ):
        return "commercial"
    if any(token in semantic_text for token in ("资格", "准入门槛", "qualification_", "supplier_qualification")):
        return "qualification"
    if any(token in location_text for token in ("评分", "评标信息", "演示", "品牌档次", "认证评分", "商务评分", "样品")):
        return "scoring"
    if any(token in location_text for token in ("技术", "标准", "检测报告", "证明材料", "参数")):
        return "technical"
    if any(token in location_text for token in ("验收", "付款", "责任", "违约", "交货", "商务")):
        return "commercial"
    if any(token in location_text for token in ("资格", "申请人的资格要求", "准入门槛")):
        return "qualification"
    return "commercial"


def _section_label_from_key(section_key: str) -> str:
    mapping = {
        "qualification": "资格条件",
        "scoring": "评分标准",
        "technical": "技术要求",
        "commercial": "商务与验收",
    }
    return mapping.get(section_key, "综合问题")


def _human_review_items(findings: list[Finding]) -> list[str]:
    items = []
    for finding in findings:
        if finding.needs_human_review and finding.human_review_reason:
            items.append(f"{finding.finding_id}：{finding.human_review_reason}")
    return items


def _refine_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
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
    refined = _merge_scoring_content_findings(refined)
    refined = _add_scoring_structure_findings(document, refined)
    refined = _add_commercial_chain_findings(document, refined)
    refined = _add_domain_match_findings(document, refined)
    refined = _add_qualification_bundle_findings(document, refined)
    refined = _add_brand_and_certification_scoring_findings(document, refined)
    refined = _add_technical_reference_consistency_findings(document, refined)
    refined = _add_commercial_burden_findings(document, refined)
    refined = _add_geographic_tendency_findings(document, refined)
    refined = _add_acceptance_boundary_findings(document, refined)
    refined = _add_liability_balance_findings(document, refined)
    refined = _add_industry_appropriateness_findings(document, refined)
    refined = _apply_finding_arbiter(refined)
    refined = _merge_technical_justification_findings(refined)
    refined = _filter_technical_justification_noise(refined)
    refined = _merge_similar_technical_findings(refined)
    refined = _merge_nearby_liability_findings(refined)
    refined = _apply_theme_splitter_and_summarizer(refined)
    refined = _drop_appendix_semantic_duplicates(refined)
    for finding in refined:
        finding.source_text = _representative_excerpt(finding.source_text)
    return refined


def _renumber_findings(findings: list[Finding]) -> list[Finding]:
    for index, finding in enumerate(findings, start=1):
        finding.finding_id = f"F-{index:03d}"
    return findings


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    priority = {"high": 0, "medium": 1, "low": 2, "none": 3}
    return sorted(
        findings,
        key=lambda item: (
            priority.get(item.risk_level, 9),
            item.text_line_start,
            item.text_line_end,
            item.issue_type,
            item.problem_title,
        ),
    )


def _apply_finding_arbiter(findings: list[Finding]) -> list[Finding]:
    theme_findings = [finding for finding in findings if finding.finding_origin == "analyzer"]
    if not theme_findings:
        return findings

    filtered: list[Finding] = []
    for finding in findings:
        if finding.finding_origin == "analyzer":
            filtered.append(finding)
            continue
        if _is_finding_covered_by_theme(finding, theme_findings):
            continue
        filtered.append(finding)
    return filtered


def _is_finding_covered_by_theme(finding: Finding, themes: list[Finding]) -> bool:
    for theme in themes:
        if _theme_covers_finding(theme, finding):
            return True
    return False


def _theme_covers_finding(theme: Finding, finding: Finding) -> bool:
    if not _line_ranges_overlap(theme, finding, tolerance=4):
        return False

    title = theme.problem_title
    if "多个方案评分项大量使用主观分档且缺少量化锚点" in title:
        return finding.issue_type == "ambiguous_requirement" and _is_scoring_finding(finding)

    if "现场演示分值过高且签到要求形成额外门槛" in title:
        return finding.issue_type in {
            "ambiguous_requirement",
            "excessive_scoring_weight",
            "geographic_restriction",
        } and _text_contains_any(
            finding,
            ("演示", "原型", "PPT", "视频", "签到", "60分钟", "60 分钟", "得 0 分"),
        )

    if "人员与团队评分混入错位证书并过度堆叠条件" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "irrelevant_certification_or_award",
            "excessive_scoring_weight",
        } and _text_contains_any(
            finding,
            ("项目负责人", "项目团队", "职称", "证书", "奖项", "荣誉", "项目经验", "特种设备"),
        )

    if "商务评分将企业背景和一般财务能力直接转化为高分优势" in title:
        return finding.issue_type in {
            "excessive_supplier_qualification",
            "excessive_scoring_weight",
            "scoring_content_mismatch",
        } and _text_contains_any(
            finding,
            ("注册资本", "营业收入", "净利润", "标准", "标准委员会"),
        )

    if "评分项名称、内容和评分证据之间不一致" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "excessive_supplier_qualification",
            "irrelevant_certification_or_award",
        } and _text_contains_any(
            finding,
            ("工程案例", "CMA", "检测报告", "资产总额", "营业收入", "净利润", "标准委员会", "科技型中小企业", "ISO20000"),
        )

    if "付款条件与履约评价结果深度绑定且评价标准开放" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "other",
        } and _text_contains_any(
            finding,
            ("履约评价", "阶段款", "支付", "评价标准", "评价指标", "解除合同", "扣款"),
        )

    if "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "unclear_acceptance_standard",
            "geographic_restriction",
            "other",
        } and _text_contains_any(
            finding,
            ("付款", "验收", "送检", "检测", "专家评审", "24小时", "到场", "解除合同", "实际需求", "质保期", "售后服务保证金"),
        )

    if "资格条件中存在与标的域不匹配的资质或登记要求" in title:
        return finding.issue_type == "qualification_domain_mismatch"

    if "资格条件中存在与标的域不匹配的行业资质或专门许可" in title:
        return finding.issue_type in {"qualification_domain_mismatch", "excessive_supplier_qualification"} and _text_contains_any(
            finding,
            ("水运工程监理", "有害生物防制", "SPCA", "特种设备"),
        )

    if "资格条件设置一般财务和规模门槛" in title:
        return finding.issue_type in {
            "excessive_supplier_qualification",
        } and _text_contains_any(
            finding,
            ("纳税", "员工总数", "资产总额", "参保人数", "月均参保", "社保"),
        )

    if "资格条件设置经营年限、属地场所或单项业绩门槛" in title:
        return finding.issue_type in {
            "qualification_domain_mismatch",
            "excessive_supplier_qualification",
            "geographic_restriction",
        } and _text_contains_any(
            finding,
            ("成立日期", "成立时间", "高新区", "固定的售后服务场所", "单项合同金额", "经营地址", "主城四区", "福州市"),
        )

    if "资格条件整体超出法定准入和履约必需范围" in title:
        return finding.issue_type in {
            "excessive_supplier_qualification",
            "qualification_domain_mismatch",
            "geographic_restriction",
        } and _text_contains_any(
            finding,
            ("纳税", "参保人数", "员工总数", "资产总额", "成立日期", "固定的售后服务场所", "经营地址", "单项合同金额", "有害生物防制", "SPCA", "棉花加工资格", "水运工程监理"),
        )

    if "评分项直接按品牌档次赋分" in title:
        return finding.issue_type in {"brand_or_model_designation", "scoring_content_mismatch"} and _text_contains_any(
            finding,
            ("一线品牌", "国际知名品牌", "格力", "美的", "海尔", "大金", "日立"),
        )

    if "认证评分混入错位证书且高分值结构失衡" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "irrelevant_certification_or_award",
            "scoring_structure_imbalance",
        } and _text_contains_any(
            finding,
            ("科技型中小企业", "高空清洗", "CCRC", "ISO20000", "认证证书", "体系认证"),
        )

    if "评分项中存在与标的域不匹配的证书认证或模板内容" in title:
        return finding.issue_type == "scoring_content_mismatch" and _is_scoring_finding(finding)

    if "技术要求中混入与标的不匹配的标准引用和检测报告形式限制" in title:
        return finding.issue_type in {"technical_justification_needed", "template_mismatch", "scoring_content_mismatch"} and _text_contains_any(
            finding,
            ("QB/T", "CMA", "本市具有检验检测机构", "权威质检部门", "检测报告原件扫描件", "2022 年起"),
        )

    if "技术要求引用了与标的不匹配的标准或规范" in title:
        return finding.issue_type in {"technical_justification_needed", "template_mismatch", "scoring_content_mismatch"} and _text_contains_any(
            finding,
            ("QB/T", "GB 6249", "GB 15605", "QB/T 1649", "QB/T 4089", "空气质量检测装置", "菜肴罐头", "聚苯乙烯泡沫包装材料"),
        )

    if "技术证明材料形式要求过严且带有地方化限制" in title:
        return finding.issue_type in {"technical_justification_needed", "template_mismatch", "scoring_content_mismatch"} and _text_contains_any(
            finding,
            ("本市具有检验检测机构", "带有 CMA", "带有CMA", "权威质检部门", "检测报告原件扫描件", "2022 年起", "国家级检测中心", "检验报告", "相关检测报告"),
        )

    if "文件中存在与标的域不匹配的模板残留或义务外扩" in title:
        return finding.issue_type in {"template_mismatch", "other"}

    if "混合采购场景叠加自动化设备和信息化接口义务，边界不清" in title:
        return finding.issue_type in {"template_mismatch", "other", "technical_justification_needed"} and _text_contains_any(
            finding,
            ("信息化管理系统", "系统端口", "无缝对接", "综合业务协同平台", "自动化调剂", "发药机", "药瓶清洁", "系统进行管理维护"),
        )

    if "商务条款叠加设置异常资金占用、交货期限和责任负担" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "unclear_acceptance_standard",
            "other",
        } and _text_contains_any(
            finding,
            ("履约担保", "备用金", "1000", "报验", "送检", "专家评审", "百分之三十", "一切损失"),
        )

    if "商务条款设置异常资金占用安排" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "other",
        } and _text_contains_any(
            finding,
            ("履约担保", "备用金", "售后服务保证金", "质保期结束", "现金形式", "5%", "36个月"),
        )

    if "交货期限设置异常或明显失真" in title:
        return finding.issue_type in {"one_sided_commercial_term", "other"} and _text_contains_any(
            finding,
            ("1000", "交货"),
        )

    if "验收送检、检测和专家评审费用整体转嫁给供应商" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "unclear_acceptance_standard",
            "other",
        } and _text_contains_any(
            finding,
            ("报验", "送检", "检测报告", "专家评审", "自行消化"),
        )

    if "商务责任和违约后果设置明显偏重" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "other",
        } and _text_contains_any(
            finding,
            ("一切损失", "违约金", "30%", "百分之三十", "负全责", "全部负责"),
        )

    if "验收程序、复检与最终确认边界不清" in title:
        return finding.issue_type in {
            "unclear_acceptance_standard",
            "one_sided_commercial_term",
            "other",
        } and _text_contains_any(
            finding,
            ("验收报告", "最终验收结果", "复检", "技术验收", "商务验收", "开箱检验"),
        )

    if "驻场、短时响应或服务场地要求形成事实上的属地倾斜" in title:
        return finding.issue_type in {"geographic_restriction", "personnel_restriction"} and _text_contains_any(
            finding,
            ("1小时", "1 小时", "60分钟", "60 分钟", "高新区内", "固定的售后服务场所", "驻场", "现场服务"),
        )

    if "评分和技术要求中存在行业适配性不足的错位内容" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "technical_justification_needed",
            "template_mismatch",
            "qualification_domain_mismatch",
        } and _text_contains_any(
            finding,
            ("水运工程监理", "高空清洗", "CCRC", "ISO20000", "空气质量检测装置", "菜肴罐头"),
        )

    if "评分结构中多类高分因素集中出现" in title:
        return finding.issue_type == "excessive_scoring_weight"

    return False


def _line_ranges_overlap(left: Finding, right: Finding, *, tolerance: int = 0) -> bool:
    return not (
        left.text_line_end + tolerance < right.text_line_start
        or right.text_line_end + tolerance < left.text_line_start
    )


def _text_contains_any(finding: Finding, markers: tuple[str, ...]) -> bool:
    haystack = " ".join(
        part
        for part in (
            finding.problem_title,
            finding.source_text,
            finding.section_path or "",
            finding.source_section or "",
        )
        if part
    )
    return any(marker in haystack for marker in markers)


def _is_scoring_finding(finding: Finding) -> bool:
    haystack = " ".join(part for part in (finding.section_path or "", finding.source_section or "") if part)
    return "评标信息" in haystack or "评分" in haystack


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
    if not finding.section_path:
        return False
    normalized = "".join(finding.section_path.split())
    return "第四章" in normalized and "投标文件组成要求及格式" in normalized


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


def _drop_appendix_semantic_duplicates(findings: list[Finding]) -> list[Finding]:
    primary = [finding for finding in findings if not _is_appendix_duplicate_candidate(finding)]
    appendix = [finding for finding in findings if _is_appendix_duplicate_candidate(finding)]
    filtered = list(primary)
    for finding in appendix:
        if any(_is_semantic_duplicate_of_primary(finding, existing) for existing in primary):
            continue
        filtered.append(finding)
    filtered.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return filtered


def _is_semantic_duplicate_of_primary(candidate: Finding, primary: Finding) -> bool:
    if candidate.issue_type != primary.issue_type:
        return False
    if candidate.clause_id and primary.clause_id and candidate.clause_id == primary.clause_id:
        return True
    if candidate.problem_title == primary.problem_title and _signatures_overlap(candidate.source_text, primary.source_text):
        return True
    if _signatures_overlap(candidate.source_text, primary.source_text) and _line_ranges_overlap(candidate, primary, tolerance=3):
        return True
    return False


def _signatures_overlap(left: str, right: str) -> bool:
    left_sig = _normalized_source_signature(left)
    right_sig = _normalized_source_signature(right)
    if not left_sig or not right_sig:
        return False
    return left_sig == right_sig or left_sig in right_sig or right_sig in left_sig


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
        if finding.finding_origin == "analyzer":
            merged.append(finding)
            continue
        family = _technical_justification_family_key(finding)
        if family is None:
            merged.append(finding)
            continue
        _apply_technical_justification_theme(finding, family, merged_count=1)
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
    left_family = _technical_justification_family_key(left)
    right_family = _technical_justification_family_key(right)
    if left_family == "fixed_year_requirement" and right_family == "fixed_year_requirement":
        return left.document_name == right.document_name
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
    _apply_technical_justification_theme(target, family, merged_count=2)


def _technical_justification_family_key(finding: Finding) -> str | None:
    normalized = _normalized_source_signature(finding.source_text)
    if any(token in normalized for token in ("生产日期必须是", "生产日期", "2025年", "固定年份")):
        return "fixed_year_requirement"
    if any(token in normalized for token in ("阻燃", "抗菌", "抗病毒", "防霉", "环保", "致癌染料", "有机锡", "邻苯", "含氯苯酚", "盐雾")):
        return "safety_environment"
    if any(token in normalized for token in ("cma", "cnas", "第三方", "检测报告")):
        return "testing_proof"
    return "technical_justification_general"


def _technical_justification_title(family: str) -> str:
    titles = {
        "fixed_year_requirement": "固定年份或过窄时点要求可能合理但需补充必要性论证",
        "safety_environment": "安全环保类技术要求可能合理但需补充必要性论证",
        "testing_proof": "检测证明形式要求可能合理但需补充必要性论证",
        "technical_justification_general": "技术要求可能合理但需补充必要性论证",
    }
    return titles.get(family, "技术要求可能合理但需补充必要性论证")


def _apply_technical_justification_theme(finding: Finding, family: str, *, merged_count: int) -> None:
    title = _technical_justification_title(family)
    if merged_count > 1:
        title = f"{title}（相邻条款已合并）"
    finding.problem_title = title
    finding.why_it_is_risky = _technical_justification_rationale(family)
    finding.rewrite_suggestion = _technical_justification_rewrite(family)
    finding.human_review_reason = _technical_justification_human_review_reason(family)


def _technical_justification_rationale(family: str) -> str:
    mapping = {
        "fixed_year_requirement": (
            "相邻技术条款对生产日期、供货时点或新旧程度提出较窄要求，建议作为一个风险点统筹论证。"
            "此类要求不当然违规，但采购人应补充限定固定年份或固定时点的设备性能必要性、市场可得性以及是否存在更中性的替代表达。"
            "建议论证方向包括：固定时点与性能稳定性是否存在直接关联、市场上可供竞争的型号范围、以及改为“全新未使用且满足交付要求”后是否仍能实现采购目标。"
        ),
        "safety_environment": (
            "相邻技术条款涉及安全、环保、院感或有害物质限制等同类要求，建议作为一个风险点统筹论证。"
            "此类要求不当然违规，但应补充适用场景、标准依据、风险控制目标和市场可竞争性说明。"
            "建议论证方向包括：该类指标是否由法律法规或临床场景直接要求、拟控制的具体风险是什么、以及是否可以用更通用的国家或行业标准替代表达。"
        ),
        "testing_proof": (
            "相邻技术条款对第三方检测、证明形式或报告时段提出同类要求，建议作为一个风险点统筹论证。"
            "此类要求不当然违规，但应补充为什么必须限定证明机构、报告时段和证明形式，以及是否存在更中性的验证方式。"
            "建议论证方向包括：证明时点与当前供货质量的关联、是否必须限定本地或特定资质机构、以及投标阶段能否接受等效证明材料。"
        ),
    }
    return mapping.get(
        family,
        "相邻技术条款涉及同类约束条件，建议作为一个风险点统筹论证。此类要求不当然违规，但应补充场景必要性、标准依据、市场可得性和更中性表达的可行性说明。",
    )


def _technical_justification_rewrite(family: str) -> str:
    mapping = {
        "fixed_year_requirement": "建议将固定年份改为全新、未使用且满足交付和质保要求的表述；如确需限定时点，应同步补充性能、安全和运维上的必要性说明，并说明不存在更中性替代表达的原因。",
        "safety_environment": "建议按适用标准、场景风险和验收目标统一说明保留范围，能以国家或行业标准表达的尽量避免叠加细化指标；如保留更高要求，应同步写明对应风险控制目标。",
        "testing_proof": "建议统一说明检测证明的适用范围、报告时段和证明机构要求，优先采用国家或行业通用标准和更中性的验证方式；如确需限定，应说明限定理由和可接受的等效证明边界。",
    }
    return mapping.get(
        family,
        "建议对同一技术组的相邻条款统一说明适用场景、标准依据、证明方式和市场可竞争性，能以国家或行业标准表达的尽量避免叠加细化证明形式。",
    )


def _technical_justification_human_review_reason(family: str) -> str:
    mapping = {
        "fixed_year_requirement": "需结合设备更新周期、性能要求、市场可得性和是否存在更中性时点表达判断固定年份要求是否应保留。",
        "safety_environment": "需结合安全、环保、院感或有害物质控制要求及市场可得性判断该类技术要求是否应保留。",
        "testing_proof": "需结合适用标准、证明机构选择依据和更中性的验证方式判断该证明形式要求是否应保留。",
    }
    return mapping.get(
        family,
        "需结合采购场景、适用标准、市场可得性和是否存在更中性表达判断该技术要求是否应保留。",
    )


def _add_scoring_structure_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    findings = _add_scoring_structure_imbalance_finding(findings)
    findings = _add_subjective_scoring_theme_finding(document, findings)
    findings = _add_demo_mechanism_theme_finding(document, findings)
    findings = _add_personnel_scoring_theme_finding(document, findings)
    findings = _add_business_strength_theme_finding(document, findings)
    findings = _add_scoring_semantic_consistency_theme_finding(document, findings)
    return findings


def _add_commercial_chain_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    findings = _add_payment_evaluation_chain_finding(document, findings)
    findings = _add_commercial_lifecycle_theme_finding(document, findings)
    return findings


def _add_domain_match_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    findings = _add_qualification_domain_theme_finding(document, findings)
    findings = _add_scoring_domain_theme_finding(document, findings)
    findings = _add_mixed_scope_boundary_theme_finding(document, findings)
    findings = _add_template_domain_theme_finding(document, findings)
    findings = _add_qualification_industry_appropriateness_finding(document, findings)
    return findings


def _add_qualification_bundle_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    findings = _add_qualification_financial_scale_theme_finding(document, findings)
    findings = _add_qualification_operating_scope_theme_finding(document, findings)
    findings = _add_qualification_reasoning_theme_finding(document, findings)
    return findings


def _add_qualification_financial_scale_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("资格条件设置一般财务和规模门槛" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_qualification_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "纳税总额不得低于",
                "年均纳税总额不低于",
                "员工总数不得少于",
                "月均参保人数不少于",
                "参保人数不少于",
                "平均资产总额不低于",
                "资产总额不得低于",
            )
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_supplier_qualification",
            problem_title="资格条件设置一般财务和规模门槛",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "资格章节以纳税总额、参保人数、员工人数和资产规模等一般经营指标设置准入门槛。"
                "这类一般财务和规模指标通常不能直接替代项目的实际供货和履约能力。"
            ),
            impact_on_competition_or_performance="可能把企业一般经营规模错误转化为参与门槛，明显压缩可竞争供应商范围。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议删除一般财务和规模门槛，仅保留与法定资格和履约能力直接相关的必要条件。",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
    )
    return findings


def _add_qualification_operating_scope_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("资格条件设置经营年限、属地场所或单项业绩门槛" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_qualification_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "营业执照的成立日期不得晚于",
                "成立日期必须早于",
                "固定的售后服务场所",
                "主要经营地址",
                "经营地址（非注册地址）",
                "主城四区范围内",
                "福州市",
                "单项合同金额不低于",
            )
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_supplier_qualification",
            problem_title="资格条件设置经营年限、属地场所或单项业绩门槛",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "资格章节将经营年限、异地经营场所或固定场地要求、以及单项业绩规模等条件前置为参与门槛。"
                "这类要求容易把一般经营历史、属地条件和项目规模偏好错误地转化为准入条件。"
            ),
            impact_on_competition_or_performance="可能对新进入供应商、非本地供应商或规模较小但具备履约能力的供应商形成明显排斥。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议删除经营年限、固定场所和单项合同金额类门槛，改为围绕交付能力、售后机制和必要经验设置更中性的资格要求。",
            needs_human_review=True,
            human_review_reason="需结合项目供货周期、售后机制和是否确有必要的类似经验判断相关经营年限、场所和业绩门槛是否应保留。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_qualification_industry_appropriateness_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("资格条件中存在与标的域不匹配的行业资质或专门许可" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_qualification_clause(clause)
        and any(
            marker in clause.text
            for marker in ("水运工程监理甲级", "有害生物防制", "SPCA", "特种设备安全管理和作业人员证书", "棉花加工资格")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="qualification_domain_mismatch",
            problem_title="资格条件中存在与标的域不匹配的行业资质或专门许可",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "资格章节中出现与采购标的行业属性明显不匹配的资质、专门许可或岗位证书要求。"
                "这类内容往往不是本项目法定准入条件，却会被错误前置为参与门槛。"
            ),
            impact_on_competition_or_performance="可能将与标的不相称的行业资质错误转化为准入门槛，直接缩小竞争范围。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议删除与本项目标的不匹配的行业资质、专门许可和岗位证书，仅保留法定资格及与履约直接相关的必要条件。",
            needs_human_review=True,
            human_review_reason="需结合项目主标的、法定许可边界和实际履约场景判断该类行业资质或专门许可是否确有必要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_qualification_reasoning_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("资格条件整体超出法定准入和履约必需范围" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_qualification_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "纳税总额",
                "年均纳税",
                "参保人数",
                "员工总数",
                "资产总额",
                "成立日期",
                "固定的售后服务场所",
                "主要经营地址",
                "单项合同金额",
                "水运工程监理甲级",
                "有害生物防制",
                "SPCA",
                "棉花加工资格",
                "特种设备安全管理和作业人员证书",
            )
        )
    ]
    if len(clauses) < 3:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_supplier_qualification",
            problem_title="资格条件整体超出法定准入和履约必需范围",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "资格章节同时叠加一般财务和规模门槛、经营年限或属地场所门槛，以及与标的不匹配的行业资质或专门许可。"
                "这类要求已经超出通常法定准入和履约必需能力判断范围，容易把一般经营状况、地域条件和错位资质整体前置为准入门槛。"
            ),
            impact_on_competition_or_performance="可能系统性压缩竞争范围，使具备实际履约能力但不满足一般经营偏好的供应商被排除在外。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议先按法定主体资格、法定许可和与履约直接相关的必要能力重新梳理资格条件，删除一般财务规模、属地场所、经营年限和错位行业资质等非必需门槛。",
            needs_human_review=True,
            human_review_reason="需结合项目主标的、法定准入要求和实际履约模式判断资格条件中哪些属于法定许可，哪些应从准入门槛回退为更中性的履约要求。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_brand_and_certification_scoring_findings(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    findings = _add_brand_scoring_theme_finding(document, findings)
    findings = _add_certification_scoring_theme_finding(document, findings)
    return findings


def _add_technical_reference_consistency_findings(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    findings = _add_technical_standard_mismatch_theme_finding(document, findings)
    findings = _add_proof_formality_findings(document, findings)
    return findings


def _add_commercial_burden_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    findings = _add_commercial_financing_burden_theme_finding(document, findings)
    findings = _add_delivery_deadline_anomaly_theme_finding(document, findings)
    findings = _add_commercial_acceptance_fee_shift_theme_finding(document, findings)
    return findings


def _add_technical_standard_mismatch_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("技术要求引用了与标的不匹配的标准或规范" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_technical_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "QB/T 8101",
                "QB/T 8075",
                "QB/T 4263",
                "QB/T 1649",
                "QB/T 4089",
                "GB 6249",
                "GB 15605",
                "空气质量检测装置",
                "菜肴罐头",
                "聚苯乙烯泡沫包装材料",
            )
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="technical_justification_needed",
            problem_title="技术要求引用了与标的不匹配的标准或规范",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "技术章节引用了与采购标的技术属性明显不匹配的标准或规范。"
                "这类标准错位通常意味着模板复制、标准引用失当或把无关规范转化为技术门槛。"
            ),
            impact_on_competition_or_performance="可能错误压缩符合条件的产品范围，并增加技术复核和投诉争议风险。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；政府采购需求编制常见问题分析（中国政府采购网）",
            rewrite_suggestion="建议删除与采购标的不匹配的标准或规范，仅保留与本项目技术性能和验收直接相关的国家、行业或通用标准。",
            needs_human_review=True,
            human_review_reason="需结合采购标的技术属性、适用标准边界和市场通行做法判断相关标准引用是否确有必要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_proof_formality_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("技术证明材料形式要求过严且带有地方化限制" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_technical_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "本市具有检验检测机构",
                "带有 CMA",
                "带有CMA",
                "权威质检部门",
                "检测报告原件扫描件",
                "2022 年起至投标截止之日期间",
                "国家级检测中心出具的检验报告",
                "提供相关检测报告",
                "提供国家级检测中心出具的检验报告",
            )
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="technical_justification_needed",
            problem_title="技术证明材料形式要求过严且带有地方化限制",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "技术章节对检测机构地域、报告时段、CMA 标识和原件扫描件形式作了叠加限制。"
                "这类证明形式要求容易把验证方式进一步收窄为特定材料路径，抬高证明成本。"
            ),
            impact_on_competition_or_performance="可能显著提高供应商举证成本，并缩窄可接受的证明材料范围。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；政府采购需求编制常见问题分析（中国政府采购网）",
            rewrite_suggestion="建议改为能够证明对应技术指标满足需求的有效资料，不限定本地机构、特定报告时段和原件扫描件形式。",
            needs_human_review=True,
            human_review_reason="需结合采购标的技术特征、适用标准和市场可得性判断相关证明形式限制是否确有必要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_commercial_financing_burden_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("商务条款设置异常资金占用安排" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "预算金额的5%作为履约担保",
                "以现金形式缴纳采购预算的5%作为履约保证金",
                "诚信履约备用金",
                "自动转为",
                "售后服务保证金",
                "质保期结束（36个月）",
                "36个月",
            )
        )
    ]
    if len(clauses) < 1:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="商务条款设置异常资金占用安排",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务条款通过现金形式履约保证金、验收后自动转售后保证金以及较长质保占压等方式叠加设置资金占用安排。"
                "这类资金占用设计会明显增加供应商的前期履约成本和现金流压力。"
            ),
            impact_on_competition_or_performance="可能显著抬高报价和资金占用成本，并压缩可参与竞争的供应商范围。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议分别校准履约担保比例和备用金安排，不宜通过叠加式资金占用条件整体提高供应商履约门槛。",
            needs_human_review=True,
            human_review_reason="需结合财政支付、履约担保和项目供货周期判断相关商务安排是否合理并符合采购内控要求。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_delivery_deadline_anomaly_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("交货期限设置异常或明显失真" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("1000      个日历日内交货", "1000 个日历日内交货", "1000个日历日内交货")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="交货期限设置异常或明显失真",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "商务条款设置了与通常电子仪器仪表供货节奏明显不匹配的超长交货期限。"
                "这类失真的交货安排容易掩盖真实供货周期要求，也会增加合同履行和验收节点的不确定性。"
            ),
            impact_on_competition_or_performance="可能导致项目排期、履约责任和验收节点失真，并增加后续履约争议风险。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；中华人民共和国民法典",
            rewrite_suggestion="建议结合采购清单、供货周期和安装调试安排重设合理交货期限，避免使用明显失真的超长交付时限。",
            needs_human_review=True,
            human_review_reason="需结合采购内容、安装调试周期和项目建设时序判断当前交货期限是否属于录入错误或异常设置。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_commercial_acceptance_fee_shift_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("验收送检、检测和专家评审费用整体转嫁给供应商" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("报验", "送检", "检测报告出具", "专家评审", "自行消化")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="unclear_acceptance_standard",
            problem_title="验收送检、检测和专家评审费用整体转嫁给供应商",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "验收条款将报验、送检、检测报告出具和专家评审等费用整体要求由供应商自行消化。"
                "当费用承担边界不随原因、责任和触发条件区分时，容易造成验收成本和争议风险单向转嫁。"
            ),
            impact_on_competition_or_performance="可能抬高供应商综合报价，并增加验收环节的费用争议和履约不确定性。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议区分法定抽检、常规验收、复检和专家评审等费用承担边界，不宜笼统要求所有相关费用均由供应商承担。",
            needs_human_review=True,
            human_review_reason="需结合验收流程、送检触发条件和责任分担规则判断相关费用转嫁安排是否合理。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_scoring_structure_imbalance_finding(findings: list[Finding]) -> list[Finding]:
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


def _add_subjective_scoring_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("多个方案评分项大量使用主观分档" in finding.problem_title for finding in findings):
        return findings
    candidates = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("评审为优", "评审为良", "评审为中", "评审为差"))
    ]
    if len(candidates) < 3:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=candidates,
            issue_type="scoring_structure_imbalance",
            problem_title="多个方案评分项大量使用主观分档且缺少量化锚点",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "多个技术方案评分项重复使用“优/良/中/差”式分档，且缺少可核验的量化锚点。"
                "当同类主观分档在整张评分表中反复出现时，评委自由裁量空间会被系统性放大，评分结构也更容易失衡。"
            ),
            impact_on_competition_or_performance="可能使技术方案评分整体偏主观，增加评审尺度不一致和复核困难。",
            legal_or_policy_basis="主观评审客观化分析（中国政府采购网）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议按需求理解、架构设计、功能覆盖、实施组织和验收衔接等分项设置量化标准，避免在多个评分项中重复使用大幅跳档的主观分档。",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
    )
    return findings


def _add_demo_mechanism_theme_finding(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("现场演示分值过高且签到要求形成额外门槛" in finding.problem_title for finding in findings):
        return findings
    demo_scoring_clauses = [
        clause
        for clause in document.clauses
        if any(marker in clause.text for marker in ("可运行展示系统", "系统原型", "PPT", "Flash", "视频"))
    ]
    sign_in_clauses = [
        clause
        for clause in document.clauses
        if any(marker in clause.text for marker in ("60 分钟内", "60分钟内", "迟到或缺席", "演示及答辩相关评分项得 0 分", "现场演示签到表"))
    ]
    clauses = [*demo_scoring_clauses, *sign_in_clauses]
    if not demo_scoring_clauses or not sign_in_clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_structure_imbalance",
            problem_title="现场演示分值过高且签到要求形成额外门槛",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "演示项对“可运行系统”“原型/PPT/视频”设置显著分差，同时要求开标后短时间内完成现场签到，未签到即相关项得0分。"
                "这会把展示形式、既有系统成熟度和现场组织条件叠加转化为高分优势。"
            ),
            impact_on_competition_or_performance="可能对具备既有成型系统、本地组织条件或现场到场能力的供应商形成明显倾斜。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议降低演示项权重，弱化展示形式差异，不宜将短时签到和现场到场条件直接与高分值绑定。",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
    )
    return findings


def _add_personnel_scoring_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("人员与团队评分混入错位证书并过度堆叠条件" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and any(
            marker in f"{clause.section_path or ''} {clause.text}"
            for marker in ("拟安排项目负责人情况", "拟安排的项目团队成员情况", "项目负责人", "团队成员")
        )
        and any(
            marker in clause.text
            for marker in (
                "学位",
                "博士",
                "硕士",
                "职称证书",
                "高级工程师",
                "CISE",
                "PMP",
                "人工智能应用工程师",
                "大数据应用工程师",
                "奖项",
                "荣誉",
                "项目经验",
                "特种设备",
            )
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="人员与团队评分混入错位证书并过度堆叠条件",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "人员与团队评分同时叠加学历、职称、注册证书、奖项、项目经验等多类因素，并混入与岗位职责或采购标的不完全匹配的证书内容。"
                "这类设计容易把团队包装能力放大为决定性竞争优势，弱化对实际岗位能力和项目履约分工的评价。"
            ),
            impact_on_competition_or_performance="可能显著抬高投标门槛，并使评分重心从团队履约能力转向证书与荣誉堆叠。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；奖项荣誉信用等级评分问题（中国政府采购网）",
            rewrite_suggestion="建议将人员评分压缩为少量与岗位职责、项目实施和成果交付直接相关的核心能力项，删除明显错位证书以及高分值学历、职称、奖项堆叠设计。",
            needs_human_review=True,
            human_review_reason="需结合项目实际岗位需求判断各类证书、奖项和项目经验是否与平台建设履约目标直接相关。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_business_strength_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("商务评分将企业背景和一般财务能力直接转化为高分优势" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("注册资本", "营业收入", "净利润", "国家相关标准委员会", "国家标准", "行业标准"))
    ]
    if len(clauses) < 3:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_supplier_qualification",
            problem_title="商务评分将企业背景和一般财务能力直接转化为高分优势",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务评分同时将标准研究参与、注册资本、营业收入和净利润折算为高分值。"
                "这类企业背景和一般经营状况通常不能直接替代本项目的实际履约能力判断。"
            ),
            impact_on_competition_or_performance="可能把企业规模和一般财务能力转化为高分门槛，缩小竞争范围。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议删除一般财务能力、企业规模和标准研究参与类评分，仅保留与项目履约直接相关的实施保障因素。",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
    )
    return findings


def _add_scoring_semantic_consistency_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("评分项名称、内容和评分证据之间不一致" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "工程案例",
                "CMA",
                "检测报告",
                "从业人员",
                "资产总额",
                "成立时间",
                "营业收入",
                "净利润",
                "标准委员会",
                "科技型中小企业",
                "高空清洗",
                "CCRC",
                "ISO20000",
                "有机产品认证",
                "生活垃圾分类",
            )
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="评分项名称、内容和评分证据之间不一致",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "多个评分项在名称上分别对应方案、商务、认证或团队能力，但实际计分内容却混入工程案例、检测证明形式、一般经营指标、企业称号或跨领域证书。"
                "当评分项名称、评分内容和评分证据之间不一致时，评审重心会明显偏离项目实际履约能力。"
            ),
            impact_on_competition_or_performance="可能把与评分主题无关或与标的不匹配的材料转化为得分点，扭曲整张评分表的评审逻辑。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议逐项校正评分项名称、评分内容与评分证据之间的对应关系，删除与评分主题不一致的案例、证明形式、企业经营指标和跨领域证书。",
            needs_human_review=True,
            human_review_reason="需结合每个评分项的评审目标、取证方式和项目履约重点判断其名称、内容和证据是否保持一致。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_payment_evaluation_chain_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("付款条件与履约评价结果深度绑定且评价标准开放" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "结合履约评价结果支付",
                "支付对应阶段款",
                "对应阶段款不予支付",
                "评价标准",
                "评价指标",
                "分值",
                "项目负责人可根据项目要求自行设定",
                "连续两次被评级为“中”",
                "累计扣款金额达到合同金额的 30%",
                "甲方有权解除合同",
            )
        )
    ]
    if len(clauses) < 3:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="付款条件与履约评价结果深度绑定且评价标准开放",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "条款将阶段付款与履约评价结果直接绑定，同时允许“评价标准、评价指标和分值”在履约过程中由项目负责人根据项目要求自行设定。"
                "当付款比例、整改要求和解除合同条件都受单方评价结果控制时，供应商回款和履约边界会明显失稳。"
            ),
            impact_on_competition_or_performance="可能导致付款条件和履约责任边界过度依赖采购人单方评价，增加报价不确定性和合同争议风险。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议预先固定履约评价标准、付款节点、整改条件和解除合同条件，不宜将付款比例和解除后果交由履约过程中单方开放式设定。",
            needs_human_review=True,
            human_review_reason="需结合合同文本、财政支付流程和履约考核制度判断付款与评价绑定的范围、比例和标准是否合理。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_commercial_lifecycle_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "付款",
                "支付",
                "验收",
                "送检",
                "检测",
                "专家评审",
                "24小时",
                "到场",
                "解除合同",
                "实际需求为准",
                "售后服务保证金",
                "复检",
                "最终验收结果",
            )
        )
    ]
    if len(clauses) < 4:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务与验收条款将付款节点、验收判定、送检复检费用、售后到场时限、解除合同和兜底责任串联在一起，形成对供应商整体偏重的履约后果链。"
                "当这些后果叠加出现时，供应商不仅承担较高的履约成本，也难以预判回款、整改和责任边界。"
            ),
            impact_on_competition_or_performance="可能提高报价不确定性和合同争议风险，并通过整体偏重的履约后果抬高投标门槛。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议按交付、验收、复检、售后和责任承担分别设置条款，删除开放式义务和单方后果，确保回款条件、到场要求和责任边界可预见、可执行。",
            needs_human_review=True,
            human_review_reason="需结合财政支付节点、验收流程和售后服务模式判断全链路责任配置是否超过项目实际履约需要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_qualification_domain_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("资格条件中存在与标的域不匹配的资质或登记要求" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(marker in clause.text for marker in ("有害生物防制", "SPCA", "特种设备安全管理和作业人员证书"))
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="qualification_domain_mismatch",
            problem_title="资格条件中存在与标的域不匹配的资质或登记要求",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "资格条件中出现与当前采购标的领域不匹配的资质、登记或专门证书要求。"
                "这类内容往往意味着模板错贴，或者把与项目履约无直接关系的条件错误地前置为参与门槛。"
            ),
            impact_on_competition_or_performance="可能将与标的不相称的行业资质错误转化为准入门槛，直接缩小竞争范围。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议删除与当前采购标的不匹配的资质、登记和专门证书要求，仅保留与法定资格和项目履约直接相关的条件。",
            needs_human_review=True,
            human_review_reason="需结合项目主标的、行业许可边界和实际履约场景判断该类资质是否确有必要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_scoring_domain_theme_finding(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("评分项中存在与标的域不匹配的证书认证或模板内容" in finding.problem_title for finding in findings):
        return findings
    domain = _document_domain(document)
    mismatch_markers = _domain_mismatch_markers(domain)
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause) and any(marker in clause.text for marker in mismatch_markers)
    ]
    if len(clauses) < 1:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="评分项中存在与标的域不匹配的证书认证或模板内容",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分项中出现与当前采购标的领域不匹配的证书、认证范围或专门行业内容。"
                "这类内容容易把模板残留或跨领域材料错误地转化为得分点，扭曲评审重心。"
            ),
            impact_on_competition_or_performance="可能使评分重心偏离项目实际履约能力，并对少数具备无关材料的供应商形成倾斜。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；奖项荣誉信用等级评分问题（中国政府采购网）",
            rewrite_suggestion="建议删除与当前采购标的不匹配的证书、认证和行业内容，仅保留与评分主题和履约目标直接相关的因素。",
            needs_human_review=True,
            human_review_reason="需结合项目主标的、评分主题和具体证书用途判断该类内容是否属于明显错位或仍有合理业务关联。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_mixed_scope_boundary_theme_finding(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("混合采购场景叠加自动化设备和信息化接口义务，边界不清" in finding.problem_title for finding in findings):
        return findings
    domain = _document_domain(document)
    if domain != "medical_tcm_mixed":
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "信息化管理系统",
                "系统端口",
                "无缝对接",
                "综合业务协同平台",
                "自动化调剂",
                "发药机",
                "药瓶清洁",
                "系统进行管理维护",
            )
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="template_mismatch",
            problem_title="混合采购场景叠加自动化设备和信息化接口义务，边界不清",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "文件在中药配方颗粒采购中叠加了自动化设备配套、信息化系统端口无缝对接、系统维护和药瓶清洁等多类义务。"
                "当药品供货、自动化设备配套和信息化接口开发被混合写入同一采购范围时，容易导致采购边界不清、履约责任外扩和供应商范围被不当收窄。"
            ),
            impact_on_competition_or_performance="可能将药品供货以外的自动化设备和信息化接口义务一并转嫁给供应商，抬高履约门槛并增加争议风险。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；政府采购需求编制常见问题分析（中国政府采购网）",
            rewrite_suggestion="建议将中药配方颗粒供货、自动化设备配套和信息化接口开发分开表述；与本次药品采购不直接相关的系统维护、药瓶清洁和扩展服务内容应删除或另行采购。",
            needs_human_review=True,
            human_review_reason="需结合本次采购边界、现有自动化设备建设情况和信息化接口职责分工判断相关配套义务是否应并入当前采购范围。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_brand_scoring_theme_finding(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("评分项直接按品牌档次赋分" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in ("一线品牌", "国际知名品牌", "格力", "美的", "海尔", "大金", "日立", "其他国产品牌")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="brand_or_model_designation",
            problem_title="评分项直接按品牌档次赋分",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分项直接列举国内一线品牌、国际知名品牌并按品牌档次赋分。"
                "这会把品牌偏好直接转化为竞争优势，而不是围绕产品性能和售后能力做客观比较。"
            ),
            impact_on_competition_or_performance="可能对其他满足采购需求的品牌形成不合理排斥，削弱公平竞争。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议删除按品牌档次直接赋分的设计，改为围绕产品性能、质保和售后能力设置客观可核验的评分因素。",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
    )
    return findings


def _add_certification_scoring_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("认证评分混入错位证书且高分值结构失衡" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in ("科技型中小企业", "高空清洗", "CCRC", "ISO20000", "认证证书")
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="认证评分混入错位证书且高分值结构失衡",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "认证评分中同时混入企业称号、跨领域证书和 IT 服务类认证，并通过较高分值结构集中放大。"
                "这类内容与电子仪器仪表供货履约关联较弱，却被整体转化为高分竞争优势。"
            ),
            impact_on_competition_or_performance="可能使评分重心偏离产品供货和售后能力，并对具备无关证书的供应商形成倾斜。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；奖项荣誉信用等级评分问题（中国政府采购网）",
            rewrite_suggestion="建议将企业称号、跨领域证书和体系认证拆开审视，仅保留与质量控制和售后履约直接相关的少量辅助性证明，并整体压降分值。",
            needs_human_review=True,
            human_review_reason="需结合采购标的、评分主题和各类认证的实际用途判断其是否与项目履约目标直接相关。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_template_domain_theme_finding(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("文件中存在与标的域不匹配的模板残留或义务外扩" in finding.problem_title for finding in findings):
        return findings
    domain = _document_domain(document)
    mismatch_markers = _domain_mismatch_markers(domain)
    clauses = [
        clause
        for clause in document.clauses
        if any(marker in clause.text for marker in mismatch_markers)
        and any(marker in clause.text for marker in ("保洁", "芯片", "系统", "安防", "设施维修", "特种设备", "垃圾", "实际需求为准"))
    ]
    if len(clauses) < 1:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="template_mismatch",
            problem_title="文件中存在与标的域不匹配的模板残留或义务外扩",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "文件中出现与当前采购标的领域不匹配的服务义务、系统对接、安防保洁或专门行业内容。"
                "这类条款通常来自跨项目模板复制，容易把无关义务和额外履约成本转嫁给供应商。"
            ),
            impact_on_competition_or_performance="可能扩张供应商义务范围，并引入与采购标的不直接相关的实施成本和争议点。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议逐条排查并删除跨领域模板残留；如确需保留，应明确其与当前采购标的的直接业务关联和履约边界。",
            needs_human_review=True,
            human_review_reason="需结合项目主标的、业务边界和合同范围判断该条款是否属于模板错贴或确有必要的扩展义务。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_geographic_tendency_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("驻场、短时响应或服务场地要求形成事实上的属地倾斜" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("1小时", "1 小时", "60分钟", "60 分钟", "高新区内", "固定的售后服务场所", "驻场", "现场服务")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="geographic_restriction",
            problem_title="驻场、短时响应或服务场地要求形成事实上的属地倾斜",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "条款同时设置驻场、短时到场响应或固定服务场地等要求。"
                "当这类要求未与明确的运维必要性绑定时，容易对本地或既有驻点供应商形成事实上的倾斜。"
            ),
            impact_on_competition_or_performance="可能抬高非本地供应商的投标准备和履约成本，间接压缩竞争范围。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议将服务保障要求改为可核验的响应机制、驻场触发条件和运维指标，不直接以短时到场或固定场地替代履约能力要求。",
            needs_human_review=True,
            human_review_reason="需结合故障等级、运维场景和响应时限必要性判断相关驻场或短时响应要求是否确有业务依据。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_acceptance_boundary_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("验收程序、复检与最终确认边界不清" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("验收报告", "最终验收结果", "复检", "技术验收", "商务验收", "开箱检验")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="unclear_acceptance_standard",
            problem_title="验收程序、复检与最终确认边界不清",
            risk_level="medium",
            severity_score=2,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "验收、复检、技术验收和商务验收等程序同时出现，但未清晰区分最终确认标准、复检触发条件和责任边界。"
                "这类设置容易在履约后期形成验收口径不一致和责任争议。"
            ),
            impact_on_competition_or_performance="可能导致验收标准不稳定、成本难估算和后续履约争议升级。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议逐条明确开箱检验、技术验收、商务验收、复检和最终确认的触发条件、结论效力及费用承担边界。",
            needs_human_review=True,
            human_review_reason="需结合项目验收流程、检测安排和责任划分规则判断各验收环节边界是否明确。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_liability_balance_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("商务责任和违约后果设置明显偏重" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("一切损失", "百分之三十的违约金", "30%的违约金", "负全责", "全部负责")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="商务责任和违约后果设置明显偏重",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务条款以“一切损失”“全部负责”或较高违约金比例等方式集中加重供应商责任。"
                "这类绝对化责任和高额后果设置容易突破合理风险分配边界。"
            ),
            impact_on_competition_or_performance="可能抬高供应商报价并扩大合同争议空间，降低潜在竞争参与意愿。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议按过错、责任原因和损失范围细化违约责任，不宜使用绝对化责任表述或明显偏高的违约后果安排。",
            needs_human_review=True,
            human_review_reason="需结合合同风险分配、赔偿边界和违约责任比例判断相关责任条款是否明显失衡。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_industry_appropriateness_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("评分和技术要求中存在行业适配性不足的错位内容" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("水运工程监理", "高空清洗", "CCRC", "ISO20000", "空气质量检测装置", "菜肴罐头")
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="评分和技术要求中存在行业适配性不足的错位内容",
            risk_level="medium",
            severity_score=2,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "评分和技术章节同时出现跨行业证书、服务认证或与当前标的明显不匹配的标准内容。"
                "这类错位内容说明文件可能存在跨项目模板拼接，容易把无关材料转化为评审或技术门槛。"
            ),
            impact_on_competition_or_performance="可能使评审重心和技术要求偏离当前采购标的，增加竞争和履约争议风险。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议结合采购标的逐条核对评分和技术章节中的证书、认证及标准引用，仅保留与本项目行业属性直接相关的内容。",
            needs_human_review=True,
            human_review_reason="需结合采购标的行业属性和具体证书、标准用途判断相关内容是否属于明显错位或仍具合理关联。",
            finding_origin="analyzer",
        )
    )
    return findings


def _document_domain(document: NormalizedDocument) -> str:
    base_text = f"{document.document_name} {document.source_path}"
    clause_text = " ".join(clause.text for clause in document.clauses[:200])
    if any(marker in base_text for marker in ("中药", "配方颗粒", "医院", "药品", "饮片")):
        if any(marker in clause_text for marker in ("自动化调剂", "发药机", "信息化管理系统", "无缝对接", "设备需求参数")):
            return "medical_tcm_mixed"
        return "medical_tcm"
    if any(marker in base_text for marker in ("平台", "信息", "软件", "系统", "数据")):
        return "information_system"
    if any(marker in base_text for marker in ("窗帘", "隔帘", "床品", "服装", "被服")):
        return "textile_goods"
    if any(marker in base_text for marker in ("发电机", "机电", "安装", "设备")):
        return "equipment_installation"
    return "general"


def _is_qualification_clause(clause) -> bool:
    text = " ".join(part for part in (clause.section_path or "", clause.source_section or "") if part)
    return "资格" in text or "申请人的资格要求" in text or "招标公告" in text


def _is_technical_clause(clause) -> bool:
    text = " ".join(part for part in (clause.section_path or "", clause.source_section or "") if part)
    return "技术要求" in text or "用户需求书" in text


def _is_commercial_clause(clause) -> bool:
    text = " ".join(part for part in (clause.section_path or "", clause.source_section or "") if part)
    return any(marker in text for marker in ("商务要求", "合同条款", "履约担保", "交货期限", "违约责任", "付款方式"))


def _domain_mismatch_markers(domain: str) -> tuple[str, ...]:
    mapping = {
        "information_system": ("园区保洁", "设施维修", "安防管理", "保洁", "垃圾", "特种设备", "高空清洗", "CCRC", "ISO20000"),
        "medical_tcm": ("IT服务管理", "生活垃圾分类", "SPCA", "有害生物防制", "棉花加工", "高空清洗", "CCRC", "ISO20000"),
        "medical_tcm_mixed": (
            "IT服务管理",
            "生活垃圾分类",
            "SPCA",
            "有害生物防制",
            "棉花加工",
            "高空清洗",
            "CCRC",
            "ISO20000",
            "园区保洁",
            "药瓶清洁",
            "无缝对接",
            "信息化管理系统",
        ),
        "textile_goods": ("芯片", "系统", "无缝对接", "平台", "软件"),
        "equipment_installation": ("有害生物防制", "SPCA", "有机产品认证", "水运机电工程专项监理", "水运工程监理甲级"),
        "general": ("园区保洁", "设施维修", "安防管理", "保洁", "芯片", "系统", "特种设备", "有害生物防制", "SPCA", "高空清洗", "CCRC", "ISO20000", "水运工程监理甲级", "棉花加工"),
    }
    return mapping.get(domain, mapping["general"])


def _is_scoring_clause(clause) -> bool:
    section_path = clause.section_path or ""
    source_section = clause.source_section or ""
    table_label = clause.table_or_item_label or ""
    return "评标信息" in section_path or "评分" in source_section or "评分" in table_label


def _build_theme_finding(
    *,
    document: NormalizedDocument,
    clauses,
    issue_type: str,
    problem_title: str,
    risk_level: str,
    severity_score: int,
    confidence: str,
    compliance_judgment: str,
    why_it_is_risky: str,
    impact_on_competition_or_performance: str,
    legal_or_policy_basis: str | None,
    rewrite_suggestion: str,
    needs_human_review: bool,
    human_review_reason: str | None,
    finding_origin: str,
) -> Finding:
    ordered = sorted(clauses, key=lambda clause: (clause.line_start, clause.line_end))
    first = ordered[0]
    source_text = "；".join(
        list(OrderedDict.fromkeys(clause.text for clause in ordered if clause.text))[:3]
    )
    return Finding(
        finding_id="F-000",
        document_name=document.document_name,
        problem_title=problem_title,
        page_hint=_merge_optional_text((clause.page_hint for clause in ordered), separator=" / "),
        clause_id=first.clause_id,
        source_section=first.source_section or "",
        section_path=_merge_optional_text((clause.section_path for clause in ordered if clause.section_path), separator=" / "),
        table_or_item_label=first.table_or_item_label,
        text_line_start=min(clause.line_start for clause in ordered),
        text_line_end=max(clause.line_end for clause in ordered),
        source_text=source_text,
        issue_type=issue_type,
        risk_level=risk_level,
        severity_score=severity_score,
        confidence=confidence,
        compliance_judgment=compliance_judgment,
        why_it_is_risky=why_it_is_risky,
        impact_on_competition_or_performance=impact_on_competition_or_performance,
        legal_or_policy_basis=legal_or_policy_basis,
        rewrite_suggestion=rewrite_suggestion,
        needs_human_review=needs_human_review,
        human_review_reason=human_review_reason,
        finding_origin=finding_origin,
    )


def _apply_theme_splitter_and_summarizer(findings: list[Finding]) -> list[Finding]:
    for finding in findings:
        if finding.finding_origin != "analyzer":
            continue
        finding.source_text = _build_theme_excerpt(finding.source_text)
        if finding.problem_title == "认证评分混入错位证书且高分值结构失衡":
            finding.why_it_is_risky = (
                "认证评分同时混入企业称号、跨领域证书和高权重认证项。"
                "这类内容不仅与电子仪器仪表供货履约关联较弱，还会通过高分值结构放大无关材料的竞争优势。"
            )
            finding.rewrite_suggestion = (
                "建议将企业称号、跨领域证书和体系认证拆开审视，仅保留与质量控制和售后履约直接相关的少量辅助性证明，并整体压降分值。"
            )
        if finding.problem_title == "资格条件设置一般财务和规模门槛":
            finding.why_it_is_risky = (
                "资格章节以纳税总额、参保人数、员工人数和资产规模等一般经营指标设置门槛。"
                "这类指标通常不能直接替代项目的实际供货和履约能力。"
            )
        if finding.problem_title == "资格条件设置经营年限、属地场所或单项业绩门槛":
            finding.source_text = _build_theme_excerpt(finding.source_text)
            finding.rewrite_suggestion = (
                "建议删除经营年限、异地经营场所和单项业绩规模门槛，改为围绕供货保障、配送响应和必要经验设置更中性的资格要求。"
            )
        if finding.problem_title == "资格条件中存在与标的域不匹配的行业资质或专门许可":
            finding.rewrite_suggestion = (
                "建议删除与项目标的不匹配的行业资质、专门许可和资格认定，仅保留法定生产许可和与中药配方颗粒供货直接相关的必要条件。"
            )
        if finding.problem_title == "资格条件整体超出法定准入和履约必需范围":
            finding.rewrite_suggestion = (
                "建议先按法定主体资格、法定许可和直接履约能力三层重新梳理准入条件；一般财务规模、属地场所、经营年限和错位行业资质不宜继续作为统一准入门槛。"
            )
        if finding.problem_title == "商务条款设置异常资金占用安排":
            finding.rewrite_suggestion = (
                "建议取消验收后自动转售后保证金等长期占压安排，分别校准履约担保比例、形式和退还节点，不宜通过叠加式资金占用条件整体提高供应商履约门槛。"
            )
        if finding.problem_title == "交货期限设置异常或明显失真":
            finding.rewrite_suggestion = (
                "建议按采购清单、供货周期和安装调试安排重设合理交货期限，并在文件中明确交付节点和验收衔接要求。"
            )
        if finding.problem_title == "技术要求引用了与标的不匹配的标准或规范":
            finding.rewrite_suggestion = (
                "建议逐项校核技术指标所对应的标准来源，仅保留与电子仪器仪表性能、精度和安全要求直接相关的国家或行业标准。"
            )
        if finding.problem_title == "技术证明材料形式要求过严且带有地方化限制":
            finding.rewrite_suggestion = (
                "建议将证明要求改为能证明对应性能指标满足需求的有效资料，不限定本地机构、特定起算年份和原件扫描件形式。"
            )
        if finding.problem_title == "文件中存在与标的域不匹配的模板残留或义务外扩":
            finding.rewrite_suggestion = (
                "建议将药品供货、自动化设备配套和信息化接口义务分开表述；与当前采购标的不直接相关的系统运维、清洁和扩展服务内容应删除或单列采购。"
            )
        if finding.problem_title == "评分项名称、内容和评分证据之间不一致":
            finding.why_it_is_risky = (
                "评分项名称、评分内容和评分证据之间没有保持一致，导致方案项、商务项或认证项中混入无关案例、证明形式和企业属性。"
                "这会让评审重心从履约能力偏向材料包装和取证形式。"
            )
            finding.rewrite_suggestion = (
                "建议按评分项的评审目的逐项校核计分内容和取证材料，删除与该评分主题不一致的案例、证书、经营指标和证明形式。"
            )
        if finding.problem_title == "人员与团队评分混入错位证书并过度堆叠条件":
            finding.rewrite_suggestion = (
                "建议围绕岗位职责、实施分工和交付成果压缩人员评分项，删除与岗位履约无直接关系的学历、奖项和错位证书堆叠，仅保留少量关键岗位能力证明。"
            )
        if finding.problem_title == "现场演示分值过高且签到要求形成额外门槛":
            finding.why_it_is_risky = (
                "演示章节同时放大系统成熟度、展示形式和短时到场条件的影响，容易把现场组织能力和既有产品形态转化为决定性竞争优势。"
                "这类设计通常弱于对功能理解、实施方案和可验证演示要点的客观评审。"
            )
            finding.rewrite_suggestion = (
                "建议将演示改为围绕关键业务流程和功能点的限定性验证，显著压降分值并删除短时签到、到场迟到即零分等附加门槛。"
            )
        if finding.problem_title == "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担":
            finding.rewrite_suggestion = (
                "建议将付款、验收、复检、售后到场和责任承担拆分为独立条款，分别明确触发条件、责任来源和费用边界，不宜通过开放式义务和叠加式后果整体压重供应商责任。"
            )
        finding.source_text = _select_representative_evidence(finding)
    return findings


def _build_theme_excerpt(source_text: str | None) -> str:
    if not source_text:
        return ""
    parts = [part.strip() for part in source_text.split("；") if part.strip()]
    unique_parts = list(OrderedDict.fromkeys(parts))
    if len(unique_parts) <= 2:
        return "；".join(unique_parts)
    return "；".join(unique_parts[:2]) + f" 等{len(unique_parts)}项"


def _select_representative_evidence(finding: Finding) -> str:
    source_text = finding.source_text or ""
    if not source_text:
        return ""
    parts = [part.strip() for part in source_text.split("；") if part.strip()]
    if len(parts) <= 1:
        return _clip_excerpt(source_text, limit=78)

    title = finding.problem_title
    keywords = _evidence_keywords_for_title(title)
    ranked = sorted(
        OrderedDict.fromkeys(parts),
        key=lambda part: (
            -sum(1 for keyword in keywords if keyword in part),
            len(part),
        ),
    )
    selected = [_clip_excerpt(part, limit=72) for part in ranked[:2]]
    excerpt = "；".join(selected)
    if len(ranked) > 2:
        excerpt = f"{excerpt} 等{len(ranked)}项"
    return excerpt


def _evidence_keywords_for_title(title: str) -> tuple[str, ...]:
    mapping = {
        "评分项名称、内容和评分证据之间不一致": (
            "工程案例",
            "检测报告",
            "CMA",
            "资产总额",
            "营业收入",
            "净利润",
            "标准委员会",
            "科技型中小企业",
            "ISO20000",
        ),
        "人员与团队评分混入错位证书并过度堆叠条件": (
            "学位",
            "博士",
            "硕士",
            "职称证书",
            "高级工程师",
            "奖项",
            "项目经验",
            "特种设备",
        ),
        "现场演示分值过高且签到要求形成额外门槛": (
            "可运行展示系统",
            "系统原型",
            "PPT",
            "视频",
            "60分钟",
            "签到",
            "得 0 分",
        ),
        "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担": (
            "付款",
            "验收",
            "送检",
            "检测",
            "专家评审",
            "24小时",
            "到场",
            "解除合同",
            "售后服务保证金",
        ),
    }
    return mapping.get(title, ())


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


def _merge_scoring_content_findings(findings: list[Finding]) -> list[Finding]:
    merged: list[Finding] = []
    pending: list[Finding] = []

    def flush_pending() -> None:
        if not pending:
            return
        if len(pending) == 1:
            merged.append(pending[0])
        else:
            merged.append(_build_scoring_content_finding(pending))
        pending.clear()

    for finding in sorted(findings, key=lambda item: (item.text_line_start, item.text_line_end, item.issue_type)):
        if finding.issue_type == "scoring_content_mismatch":
            if pending and not _can_merge_scoring_content(pending[-1], finding):
                flush_pending()
            pending.append(finding)
            continue
        flush_pending()
        merged.append(finding)

    flush_pending()
    merged.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return merged


def _can_merge_scoring_content(left: Finding, right: Finding) -> bool:
    if _scoring_content_family_key(left) != _scoring_content_family_key(right):
        return False
    left_section = left.section_path or ""
    right_section = right.section_path or ""
    if "评标信息" not in left_section or "评标信息" not in right_section:
        return False
    return right.text_line_start - left.text_line_end <= 120


def _build_scoring_content_finding(candidates: list[Finding]) -> Finding:
    ordered = sorted(candidates, key=lambda item: (item.text_line_start, item.text_line_end))
    base = ordered[0]
    merged = Finding(**base.to_dict())
    merged.text_line_start = min(item.text_line_start for item in ordered)
    merged.text_line_end = max(item.text_line_end for item in ordered)
    merged.page_hint = _merge_optional_text((item.page_hint for item in ordered), separator=" / ")
    merged.section_path = _merge_optional_text((item.section_path for item in ordered), separator=" / ")
    merged.source_text = "；".join(list(OrderedDict.fromkeys(item.source_text for item in ordered if item.source_text)))
    merged.problem_title = "评分内容与评分主题或采购标的不完全匹配（同一评分项已合并）"
    merged.issue_type = "scoring_content_mismatch"
    merged.risk_level = "high"
    merged.severity_score = 3
    merged.confidence = "high"
    merged.compliance_judgment = "likely_non_compliant"
    merged.why_it_is_risky = (
        "同一评分项中混入了与评分主题不一致的案例、检测报告形式、企业规模或跨领域证书等内容，建议作为一个风险点统筹修改。"
        "这类内容容易把与项目履约无直接关系的材料转化为得分点，导致评审重心偏离采购需求本身。"
    )
    merged.impact_on_competition_or_performance = "可能把与评分主题无关或与标的不匹配的材料转化为得分点，扭曲评审重心。"
    merged.legal_or_policy_basis = _merge_optional_text(
        item.legal_or_policy_basis for item in ordered if item.legal_or_policy_basis
    )
    merged.rewrite_suggestion = (
        "建议将工程案例、检测证明形式、企业规模和跨领域证书等内容移出对应评分项，仅保留与评分主题和履约目标直接相关的可核验因素。"
    )
    merged.needs_human_review = True
    merged.human_review_reason = "需结合评分主题和项目履约目标判断该评分内容是否与评审事项直接相关。"
    return merged


def _scoring_content_family_key(finding: Finding) -> str:
    text = f"{finding.problem_title} {finding.source_text}"
    if any(marker in text for marker in ("工程案例", "CMA", "检测报告")):
        return "plan_support_material"
    if any(marker in text for marker in ("从业人员", "资产总额", "成立时间")):
        return "enterprise_attribute"
    if any(marker in text for marker in ("有机产品认证", "国际标准产品", "水运机电工程专项监理")):
        return "domain_mismatch_certification"
    return "general_scoring_content"


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
    others = [
        finding
        for finding in findings
        if finding.issue_type != "one_sided_commercial_term" or finding.finding_origin == "analyzer"
    ]
    liabilities = sorted(
        (
            finding
            for finding in findings
            if finding.issue_type == "one_sided_commercial_term" and finding.finding_origin != "analyzer"
        ),
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
