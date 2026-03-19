from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from agent_compliance.analyzers.qualification import (
    _add_qualification_industry_appropriateness_finding as _qualification_industry_appropriateness_finding,
    apply_qualification_analyzers,
    looks_like_supplier_level_qualification_clause as _looks_like_supplier_level_qualification_clause,
)
from agent_compliance.analyzers.commercial import apply_commercial_analyzers
from agent_compliance.analyzers.scoring import apply_scoring_analyzers
from agent_compliance.analyzers.technical import apply_technical_analyzers
from agent_compliance.pipelines.confidence_calibrator import apply_confidence_calibrator
from agent_compliance.pipelines.effective_requirement_scope_filter import (
    classify_requirement_scope,
    filter_effective_requirement_clauses,
    is_effective_requirement_clause,
)
from agent_compliance.pipelines.rewrite_generator import apply_rewrite_generator
from agent_compliance.pipelines.procurement_stage_router import route_procurement_stage
from agent_compliance.pipelines.review_arbiter import (
    apply_finding_arbiter,
    is_qualification_like_finding as _is_qualification_like_finding,
    is_scoring_finding as _is_scoring_finding,
    line_ranges_overlap as _line_ranges_overlap,
    renumber_findings,
    sort_findings,
)
from agent_compliance.pipelines.review_evidence import (
    build_theme_excerpt as _build_theme_excerpt,
    clip_excerpt as _clip_excerpt,
    drop_appendix_semantic_duplicates as _drop_appendix_semantic_duplicates,
    is_appendix_duplicate_candidate as _is_appendix_duplicate_candidate,
    matches_existing_signature as _matches_existing_signature,
    merge_optional_text as _merge_optional_text,
    normalized_source_signature as _normalized_source_signature,
    representative_excerpt as _representative_excerpt,
    select_representative_evidence as _select_representative_evidence,
    shorten_section_path as _shorten_section_path,
)
from agent_compliance.knowledge.references_index import ReferenceRecord, find_references
from agent_compliance.knowledge.legal_authority_reasoner import apply_legal_authority_reasoner
from agent_compliance.knowledge.catalog_knowledge_profile import (
    catalog_domain_mismatch_markers_for_classification,
    catalog_mixed_scope_markers_for_classification,
    catalog_mixed_scope_core_markers_for_classification,
    catalog_mixed_scope_hard_mismatch_markers_for_classification,
    catalog_mixed_scope_out_of_scope_markers_for_classification,
    catalog_mixed_scope_support_markers_for_classification,
    catalog_template_scope_markers_for_classification,
)
from agent_compliance.knowledge.procurement_catalog import (
    CatalogClassification,
    classification_has_catalog_prefix,
    classification_has_domain,
    classify_procurement_catalog,
)
from agent_compliance.pipelines.review_strategy import (
    build_analyzer_execution_order,
    build_overall_summary,
    document_domain as _document_domain,
)
from agent_compliance.schemas import Finding, NormalizedDocument, ReviewResult, RuleHit, utc_now_iso


def build_review_result(document: NormalizedDocument, hits: list[RuleHit]) -> ReviewResult:
    classification = classify_procurement_catalog(document)
    grouped_hits = _group_hits(document, _dedupe_hits(hits))
    findings: list[Finding] = []
    for index, group in enumerate(grouped_hits, start=1):
        hit = group.primary_hit
        clause = _find_clause(document, hit)
        scope = classify_requirement_scope(
            clause_id=hit.matched_clause_id,
            section_path=clause.section_path if clause else None,
            source_section=clause.source_section if clause else hit.source_section,
            table_or_item_label=clause.table_or_item_label if clause else None,
            text=clause.text if clause else hit.matched_text,
        )
        if scope.category != "body":
            continue
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
    findings = _refine_findings(document, findings, classification=classification)

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
        ),
        document=document,
        classification=classification,
    )


def reconcile_review_result(
    review: ReviewResult,
    document: NormalizedDocument | None = None,
    classification: CatalogClassification | None = None,
) -> ReviewResult:
    stage_profile = route_procurement_stage(document=document, findings=review.findings)
    review.findings = apply_finding_arbiter(review.findings, classification=classification)
    review.findings = apply_legal_authority_reasoner(review.findings)
    review.findings = apply_rewrite_generator(
        review.findings,
        stage_profile=stage_profile,
    )
    review.findings = apply_confidence_calibrator(
        review.findings,
        classification=classification,
        stage_profile=stage_profile,
    )
    review.findings = sort_findings(review.findings)
    review.findings = renumber_findings(review.findings)
    review.overall_risk_summary = build_overall_summary(
        review.findings,
        document=document,
        classification=classification,
    )
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
        source_section = finding.source_section or ""
        if (
            finding.issue_type == "ambiguous_requirement"
            and any(
                token in section_path
                for token in (
                    "政府采购履约异常情况反馈表",
                    "评审程序及评审方法",
                    "通用条款",
                    "质疑处理",
                )
            )
        ):
            continue
        if finding.issue_type == "qualification_domain_mismatch":
            if "评分" in section_path or "评分" in source_section:
                continue
            source_text = finding.source_text or ""
            if any(marker in source_text for marker in ("上岗", "人员持有", "防制员证", "防治员证")) and not _looks_like_supplier_level_qualification_clause(source_text):
                continue
            if not _is_qualification_like_finding(finding) and not _looks_like_supplier_level_qualification_clause(source_text):
                continue
        if (
            finding.issue_type == "irrelevant_certification_or_award"
            and "其他重要条款" in section_path
            and any(marker in (finding.source_text or "") for marker in ("企业荣誉", "供应商认证情况", "同类型项目业绩及履约评价"))
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


def _human_review_items(findings: list[Finding]) -> list[str]:
    items = []
    for finding in findings:
        if finding.needs_human_review and finding.human_review_reason:
            items.append(f"{finding.finding_id}：{finding.human_review_reason}")
    return items


def _refine_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
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
    analyzer_order = build_analyzer_execution_order(refined, document=document, classification=classification)
    for analyzer_group in analyzer_order:
        if analyzer_group == "scoring":
            refined = apply_scoring_analyzers(
                document,
                refined,
                build_theme_finding=_build_theme_finding,
                is_scoring_clause=_is_scoring_clause,
                document_domain=_document_domain,
                merge_optional_text=_merge_optional_text,
                catalog_classification=classification,
            )
            continue
        if analyzer_group == "commercial":
            refined = apply_commercial_analyzers(
                document,
                refined,
                build_theme_finding=_build_theme_finding,
                is_substantive_commercial_clause=_is_substantive_commercial_clause,
                catalog_classification=classification,
            )
            continue
        if analyzer_group == "qualification":
            refined = apply_qualification_analyzers(
                document,
                refined,
                build_theme_finding=_build_theme_finding,
                is_qualification_clause=_is_qualification_clause,
                catalog_classification=classification,
            )
            continue
        if analyzer_group == "technical":
            refined = apply_technical_analyzers(
                document,
                refined,
                build_theme_finding=_build_theme_finding,
                is_technical_clause=_is_technical_clause,
                catalog_classification=classification,
            )
            continue
    refined = _add_domain_match_findings(document, refined, classification=classification)
    refined = _add_industry_appropriateness_findings(document, refined)
    refined = apply_finding_arbiter(refined, classification=classification)
    refined = _merge_technical_justification_findings(refined)
    refined = _filter_technical_justification_noise(document, refined)
    refined = _merge_similar_technical_findings(refined)
    refined = _merge_nearby_liability_findings(refined)
    refined = _apply_theme_splitter_and_summarizer(refined, classification=classification)
    refined = _drop_appendix_semantic_duplicates(refined)
    for finding in refined:
        finding.source_text = _representative_excerpt(finding.source_text)
    return refined


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


def _filter_technical_justification_noise(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    filtered: list[Finding] = []
    domain = _document_domain(document)
    for finding in findings:
        if finding.issue_type != "technical_justification_needed":
            filtered.append(finding)
            continue
        if _is_scoring_finding(finding):
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
                "商品包装政府采购需求标准",
                "快递包装政府采购需求标准",
            )
        ):
            continue
        if "国家有关安全、环保、卫生的规定" in normalized or "国家有关安全环保卫生的规定" in normalized:
            continue
        if normalized in {"抗菌抗病毒卷帘", "阻燃抑菌抗病毒隔帘", "燃抑菌抗病毒"}:
            continue
        if domain == "property_service":
            section_text = " ".join(
                part for part in (finding.section_path, finding.source_section, finding.table_or_item_label) if part
            )
            if any(marker in section_text for marker in ("商务要求", "合同条款", "违约责任", "付款方式", "验收条件")):
                continue
            if any(
                marker in normalized
                for marker in (
                    "医院评审",
                    "环保相关要求",
                    "作业符合环保要求",
                    "热水供应系统24小时运作",
                    "高低压供配电值班24小时值班",
                    "政府部门检查",
                    "反恐",
                    "消防",
                    "生活垃圾分类",
                    "绿化垃圾",
                    "化粪池压榨清掏",
                    "污水井",
                    "雨水井",
                    "医院内电池",
                )
            ):
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


def _add_domain_match_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    findings = _add_qualification_domain_theme_finding(document, findings, classification=classification)
    findings = _add_scoring_domain_theme_finding(document, findings, classification=classification)
    findings = _add_mixed_scope_boundary_theme_finding(document, findings, classification=classification)
    findings = _add_template_domain_theme_finding(document, findings, classification=classification)
    findings = _qualification_industry_appropriateness_finding(
        document,
        findings,
        build_theme_finding=_build_theme_finding,
        is_qualification_clause=_is_qualification_clause,
        catalog_classification=classification,
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
        if _is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in ("报验", "送检", "检测报告出具", "专家评审", "自行消化", "空气检测", "监理", "整改费用", "复验费用", "抽检费用")
        )
    ]
    if not clauses:
        return findings
    _append_theme_finding(
        findings,
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
        ),
    )
    return findings


def _add_liability_imbalance_theme_finding(
    document: NormalizedDocument, findings: list[Finding]
) -> list[Finding]:
    if any("商务责任和违约后果设置明显偏重" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in (
                "采购人不承担任何责任",
                "相关损失及责任均与采购人无关",
                "一切事故",
                "负全责",
                "违约金按合同总价",
                "扣除全部履约保证金",
                "从应付货款中直接扣除",
                "直接扣减合同价款",
            )
        )
    ]
    if not clauses:
        return findings
    _append_theme_finding(
        findings,
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
                "商务条款通过采购人绝对免责、供应商兜底承担全部责任以及较重违约金和扣款后果，形成了明显偏重的责任配置。"
                "当责任承担和违约后果都集中压向供应商时，合同权利义务容易失衡。"
            ),
            impact_on_competition_or_performance="可能显著提高报价不确定性和合同争议风险，并抬高供应商整体履约风险成本。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议按过错、责任来源和实际损失划分责任，删除绝对免责、当然扣款和过重违约后果设计。",
            needs_human_review=True,
            human_review_reason="需结合合同责任分配、违约情形和损失承担规则判断相关后果设置是否与项目实际履约风险相匹配。",
            finding_origin="analyzer",
        ),
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
        if _is_substantive_commercial_clause(clause)
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
                "每月服务费与考核结果挂钩",
                "管理费直接挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "按1%扣减",
                "按2%扣减",
                "按3%扣减",
                "提前告知",
                "并非最终版本",
                "及时修正《标准》",
                "无条件服从",
            )
        )
    ]
    evaluation_clauses = [
        clause
        for clause in clauses
        if any(
            marker in clause.text
            for marker in (
                "履约评价",
                "评价标准",
                "评价指标",
                "项目负责人可根据项目要求自行设定",
                "每月服务费与考核结果挂钩",
                "管理费直接挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "提前告知",
                "并非最终版本",
                "及时修正《标准》",
                "无条件服从",
            )
        )
    ]
    if len(clauses) < 3 or not evaluation_clauses:
        return findings
    _append_theme_finding(
        findings,
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
        ),
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
        if _is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in (
                "付款",
                "支付",
                "扣除当月物业服务费",
                "每低1分",
                "月得分",
                "考核不合格",
                "每月服务费与考核结果挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "按1%扣减",
                "按2%扣减",
                "按3%扣减",
                "验收",
                "送检",
                "检测",
                "专家评审",
                "24小时",
                "2小时",
                "12小时",
                "到场",
                "解除合同",
                "实际需求为准",
                "按市场价",
                "市场价格",
                "用户组织有关技术人员",
                "医院审核后方可制作",
                "其他合同未明示的相关工作",
                "必须有能力进行更改",
                "合同总价为固定不变价格",
                "售后服务保证金",
                "复检",
                "最终验收结果",
                "损失",
                "承担",
                "开机率",
                "备用设备",
                "财政审批",
                "暂停支付",
            )
        )
    ]
    focused_clauses = [
        clause
        for clause in clauses
        if any(
            marker in clause.text
            for marker in (
                "付款",
                "支付",
                "阶段款",
                "扣除当月物业服务费",
                "每低1分",
                "月得分",
                "考核不合格",
                "每月服务费与考核结果挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "按1%扣减",
                "按2%扣减",
                "按3%扣减",
                "履约评价",
                "评价标准",
                "评价指标",
                "违约金",
                "解除合同",
                "24小时",
                "2 小时",
                "12 小时",
                "1 小时",
                "48小时",
                "到场",
                "送检",
                "检测",
                "专家评审",
                "终验",
                "开机率",
                "备用设备",
                "财政审批",
                "暂停支付",
                "第三方质量检测",
                "一切损失",
                "按市场价",
                "市场价格",
                "用户组织有关技术人员",
                "医院审核后方可制作",
                "其他合同未明示的相关工作",
                "必须有能力进行更改",
                "固定不变价格",
            )
        )
    ]
    focused_clauses = _prefer_dominant_commercial_section(focused_clauses)
    responsibility_clauses = [
        clause
        for clause in focused_clauses
        if any(
            marker in clause.text
            for marker in (
                "24小时",
                "1 小时",
                "48小时",
                "解除合同",
                "违约金",
                "到场",
                "开机率",
                "备用设备",
                "一切损失",
                "扣除当月物业服务费",
                "每低1分",
                "月得分",
                "考核不合格",
            )
        )
    ]
    acceptance_clauses = [clause for clause in focused_clauses if any(marker in clause.text for marker in ("验收", "送检", "检测", "监理", "复检", "终验", "专家评审"))]
    if len(focused_clauses) < 3 or not responsibility_clauses or not acceptance_clauses:
        return findings
    _append_theme_finding(
        findings,
        _build_theme_finding(
            document=document,
            clauses=focused_clauses,
            issue_type="one_sided_commercial_term",
            problem_title="履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务与验收条款将付款节点、验收判定、送检复检费用、售后到场时限以及附加管理义务串联在一起，形成对供应商整体偏重的履约后果链。"
                "当这些后果叠加出现时，供应商不仅承担较高的履约成本，也难以预判回款、整改、到场响应和附加义务边界。"
            ),
            impact_on_competition_or_performance="可能提高报价不确定性和合同争议风险，并通过整体偏重的履约后果抬高投标门槛。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议按付款、验收、复检、售后响应和附加管理义务分别设置条款，删除开放式义务和单方后果，确保回款条件、到场要求和责任边界可预见、可执行。",
            needs_human_review=True,
            human_review_reason="需结合财政支付节点、验收流程和售后服务模式判断全链路责任配置是否超过项目实际履约需要。",
            finding_origin="analyzer",
        ),
    )
    return findings


def _add_qualification_domain_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("资格条件中存在与标的域不匹配的资质或登记要求" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_qualification_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "有害生物防制",
                "SPCA",
                "特种设备安全管理和作业人员证书",
                "生活垃圾分类服务认证证书",
                "学生饮用奶定点生产企业资格",
                "公司治理评级证书",
                "合规管理体系认证证书",
                "《合规管理体系认证证书》",
            )
        )
    ]
    if classification_has_domain(classification, "property_service"):
        clauses = [clause for clause in clauses if "特种设备安全管理和作业人员证书" not in clause.text]
    if not clauses:
        return findings
    _append_theme_finding(
        findings,
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
        ),
    )
    return findings


def _add_scoring_domain_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("评分项中存在与标的域不匹配的证书认证或模板内容" in finding.problem_title for finding in findings):
        return findings
    domain = _effective_domain_key(document, classification)
    mismatch_markers = _domain_mismatch_markers(domain, classification=classification)
    clauses = [
        clause
        for clause in document.clauses
        if _is_scoring_clause(clause)
        and not _is_explanatory_summary_clause(clause)
        and any(marker in clause.text for marker in mismatch_markers)
    ]
    if len(clauses) < 1:
        return findings
    _append_theme_finding(
        findings,
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
        ),
    )
    return findings


def _add_mixed_scope_boundary_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    existing_titles = {finding.problem_title for finding in findings}
    if (
        "混合采购场景叠加自动化设备和信息化接口义务，边界不清" in existing_titles
        or "家具采购场景叠加资产定位和智能管理系统义务，边界不清" in existing_titles
        or "物业服务场景叠加自动化系统和软件著作权评分，边界不清" in existing_titles
        or "标识标牌及宣传印制服务叠加设备保障和信息化支撑内容，边界不清" in existing_titles
        or "体育器材及运动场设施叠加轻量智能化功能，边界需进一步论证" in existing_titles
        or "设备采购中叠加医院信息系统开放对接义务，边界需复核" in existing_titles
        or "设备采购中叠加碳足迹盘查和持续改进义务，边界需复核" in existing_titles
    ):
        return findings
    domain = _effective_domain_key(document, classification)
    profile_mixed_markers = catalog_mixed_scope_markers_for_classification(classification)
    profile_core_markers = catalog_mixed_scope_core_markers_for_classification(classification)
    profile_support_markers = catalog_mixed_scope_support_markers_for_classification(classification)
    profile_out_of_scope_markers = catalog_mixed_scope_out_of_scope_markers_for_classification(classification)
    profile_hard_markers = catalog_mixed_scope_hard_mismatch_markers_for_classification(classification)
    min_out_of_scope_hits = 2
    if domain == "medical_tcm_mixed":
        mixed_markers = profile_out_of_scope_markers or (
            "信息化管理系统",
            "系统端口",
            "无缝对接",
            "综合业务协同平台",
            "自动化调剂",
            "发药机",
            "药瓶清洁",
            "系统进行管理维护",
        )
        core_markers = profile_core_markers or ("中药配方颗粒", "药品", "配送", "仓储", "供应")
        clauses = [
            clause
            for clause in document.clauses
            if is_effective_requirement_clause(clause)
            if any(marker in clause.text for marker in (*mixed_markers, *core_markers))
        ]
        out_of_scope_hits = _collect_marker_hits(clauses, mixed_markers)
        if len(out_of_scope_hits) < min_out_of_scope_hits or not any(
            any(marker in clause.text for marker in core_markers) for clause in clauses
        ):
            return findings
        hard_hits = _collect_marker_hits(clauses, profile_hard_markers or mixed_markers)
        support_hits = _collect_marker_hits(clauses, profile_support_markers)
        support_clause_count = _count_marker_clauses(clauses, profile_support_markers)
        if not hard_hits and profile_support_markers and (len(support_hits) < 3 or support_clause_count < 2):
            return findings
        title = "混合采购场景叠加自动化设备和信息化接口义务，边界不清"
        rationale = (
            "文件在中药配方颗粒采购中叠加了自动化设备配套、信息化系统端口无缝对接、系统维护和药瓶清洁等多类义务。"
            "当药品供货、自动化设备配套和信息化接口开发被混合写入同一采购范围时，容易导致采购边界不清、履约责任外扩和供应商范围被不当收窄。"
        )
        impact = "可能将药品供货以外的自动化设备和信息化接口义务一并转嫁给供应商，抬高履约门槛并增加争议风险。"
        rewrite = "建议将中药配方颗粒供货、自动化设备配套和信息化接口开发分开表述；与本次药品采购不直接相关的系统维护、药瓶清洁和扩展服务内容应删除或另行采购。"
        review_reason = "需结合本次采购边界、现有自动化设备建设情况和信息化接口职责分工判断相关配套义务是否应并入当前采购范围。"
    elif domain == "furniture_goods":
        mixed_markers = profile_out_of_scope_markers or (
            "定位管理标签模块",
            "资产管理读写基站",
            "蓝牙",
            "UWB",
            "资产定位管理系统",
            "智能芯片",
            "软件管理系统",
            "碳足迹数据",
        )
        core_markers = profile_core_markers or ("家具", "供货", "安装", "交货")
        clauses = [
            clause
            for clause in document.clauses
            if is_effective_requirement_clause(clause)
            if any(marker in clause.text for marker in (*mixed_markers, *core_markers))
        ]
        out_of_scope_hits = _collect_marker_hits(clauses, mixed_markers)
        if len(out_of_scope_hits) < min_out_of_scope_hits or not any(
            any(marker in clause.text for marker in core_markers) for clause in clauses
        ):
            return findings
        hard_hits = _collect_marker_hits(clauses, profile_hard_markers or mixed_markers)
        support_hits = _collect_marker_hits(clauses, profile_support_markers)
        support_clause_count = _count_marker_clauses(clauses, profile_support_markers)
        if not hard_hits and profile_support_markers and (len(support_hits) < 3 or support_clause_count < 2):
            return findings
        title = "家具采购场景叠加资产定位和智能管理系统义务，边界不清"
        rationale = (
            "文件在家具采购中叠加了资产定位标签模块、蓝牙或UWB定位系统、智能芯片和在线管理系统等信息化义务。"
            "当家具供货、定位管理和在线系统功能被混合写入同一采购范围时，容易导致采购边界不清，并把额外的信息化建设责任一并转嫁给供应商。"
        )
        impact = "可能将家具供货以外的定位系统、芯片管理和软件配套义务一并压给供应商，抬高履约门槛并增加争议风险。"
        rewrite = "建议将家具供货与资产定位、智能芯片和软件管理系统义务分开表述；确需配套建设的，应单独说明其业务必要性、边界和验收责任。"
        review_reason = "需结合家具采购边界、院内资产管理系统现状和是否属于独立信息化建设内容判断相关配套义务是否应并入本次采购。"
    elif domain == "property_service":
        mixed_markers = profile_out_of_scope_markers or (
            "物业垃圾分类自动化分捡类系统",
            "物业能源管理类软件",
            "物业电梯安全远程监控类系统",
            "物业消防设备监测自动化类系统",
            "物业空调运行自动化监测类系统",
            "软件著作权",
            "著作权登记证书",
        )
        core_markers = profile_core_markers or ("物业", "保洁", "安保", "维修", "驻场", "服务")
        clauses = [
            clause
            for clause in document.clauses
            if is_effective_requirement_clause(clause)
            if any(marker in clause.text for marker in (*mixed_markers, *core_markers))
        ]
        out_of_scope_hits = _collect_marker_hits(clauses, mixed_markers)
        if len(out_of_scope_hits) < min_out_of_scope_hits or not any(
            any(marker in clause.text for marker in core_markers) for clause in clauses
        ):
            return findings
        hard_hits = _collect_marker_hits(clauses, profile_hard_markers or mixed_markers)
        support_hits = _collect_marker_hits(clauses, profile_support_markers)
        support_clause_count = _count_marker_clauses(clauses, profile_support_markers)
        if not hard_hits and profile_support_markers and (len(support_hits) < 3 or support_clause_count < 2):
            return findings
        title = "物业服务场景叠加自动化系统和软件著作权评分，边界不清"
        rationale = (
            "文件在物业管理服务采购中叠加了垃圾分类自动分拣、能源管理、电梯远程监控、消防自动监测和空调运行监测等系统类软件著作权评分。"
            "当物业服务履约与多类自动化系统建设或知识产权储备被混合写入同一评分主题时，容易导致采购边界和履约重心被带偏。"
        )
        impact = "可能把物业服务以外的软件系统建设和知识产权储备一并转化为高分优势，抬高竞争门槛并偏离核心服务能力比较。"
        rewrite = "建议将物业服务能力评价与自动化系统建设能力分开表述；如确需考察数字化管理能力，应围绕实际应用场景、功能效果和服务方案设置低权重、可核验评分因素，而非直接按软件著作权储备赋分。"
        review_reason = "需结合本次物业服务采购范围、学校现有智能化设施情况和数字化管理需求判断相关系统类能力是否应并入本项目评分。"
    elif domain == "signage_printing_service":
        mixed_markers = profile_out_of_scope_markers or (
            "软件著作权",
            "UV 打印机",
            "UV打印机",
            "喷绘机",
            "写真机",
            "雕刻机",
            "折弯机",
            "系统端口",
            "无缝对接",
        )
        core_markers = profile_core_markers or ("标识", "标牌", "导视", "宣传印刷", "设计制作", "安装维护")
        clauses = [
            clause
            for clause in document.clauses
            if is_effective_requirement_clause(clause)
            if any(marker in clause.text for marker in (*mixed_markers, *core_markers))
        ]
        out_of_scope_hits = _collect_marker_hits(clauses, mixed_markers)
        if len(out_of_scope_hits) < min_out_of_scope_hits or not any(
            any(marker in clause.text for marker in core_markers) for clause in clauses
        ):
            return findings
        hard_hits = _collect_marker_hits(clauses, profile_hard_markers or mixed_markers)
        support_hits = _collect_marker_hits(clauses, profile_support_markers)
        support_clause_count = _count_marker_clauses(clauses, profile_support_markers)
        if not hard_hits and profile_support_markers and (len(support_hits) < 3 or support_clause_count < 2):
            return findings
        title = "标识标牌及宣传印制服务叠加设备保障和信息化支撑内容，边界不清"
        rationale = (
            "文件在标识标牌及宣传印制服务采购中，同时叠加了印刷设备储备、软件著作权和可能的信息化支撑内容。"
            "当设计制作服务、设备保障和系统支撑被混合写入同一采购范围时，容易导致采购边界不清，并把额外的设备和数字化能力整体转化为得分或履约前提。"
        )
        impact = "可能把标识标牌及宣传印制服务以外的设备储备和信息化支撑能力一并转化为竞争门槛，扩大履约义务边界。"
        rewrite = "建议将设计制作服务、现场安装维护、设备保障和可能的信息化支撑分开表述；如确需考察设备或数字化能力，应单独说明业务必要性、边界和验收责任。"
        review_reason = "需结合本次宣传印制服务的真实交付边界判断印刷设备储备和软件著作权等内容是必要支撑，还是被不当上浮为评分或履约要求。"
    elif domain == "medical_device_goods":
        mixed_markers = profile_out_of_scope_markers or (
            "免费开放软件端口",
            "医院信息系统",
            "HIS",
            "PACS",
            "LIS",
            "完整的数据交换",
            "数据对接产生的费用",
            "碳足迹盘查报告",
            "碳足迹改进报告",
        )
        core_markers = profile_core_markers or ("设备", "供货", "安装", "调试", "验收", "院内接口")
        clauses = [
            clause
            for clause in document.clauses
            if is_effective_requirement_clause(clause)
            if any(marker in clause.text for marker in (*mixed_markers, *core_markers))
        ]
        out_of_scope_hits = _collect_marker_hits(clauses, mixed_markers)
        has_core_context = any(any(marker in clause.text for marker in core_markers) for clause in clauses) or any(
            marker in document.document_name for marker in core_markers
        )
        if len(out_of_scope_hits) < min_out_of_scope_hits or not has_core_context:
            return findings
        hard_hits = _collect_marker_hits(clauses, profile_hard_markers or mixed_markers)
        support_hits = _collect_marker_hits(clauses, profile_support_markers)
        support_clause_count = _count_marker_clauses(clauses, profile_support_markers)
        if not hard_hits and profile_support_markers and (len(support_hits) < 3 or support_clause_count < 2):
            return findings
        interface_markers = (
            "免费开放软件端口",
            "医院信息系统",
            "HIS",
            "PACS",
            "LIS",
            "完整的数据交换",
            "数据对接产生的费用",
        )
        carbon_markers = (
            "碳足迹盘查报告",
            "碳足迹改进报告",
            "碳足迹",
            "盘查报告",
            "改进报告",
        )
        interface_clauses = [
            clause for clause in clauses if any(marker in clause.text for marker in interface_markers)
        ]
        carbon_clauses = [
            clause for clause in clauses if any(marker in clause.text for marker in carbon_markers)
        ]
        if interface_clauses:
            _append_theme_finding(
                findings,
                _build_theme_finding(
                    document=document,
                    clauses=interface_clauses,
                    issue_type="template_mismatch",
                    problem_title="设备采购中叠加医院信息系统开放对接义务，边界需复核",
                    risk_level="high",
                    severity_score=3,
                    confidence="high",
                    compliance_judgment="potentially_problematic",
                    why_it_is_risky=(
                        "文件在设备采购中要求中标人免费开放软件端口、承担医院信息系统对接责任并持续配合数据交换。"
                        "这类接口开放和系统配合义务已经超出通常设备供货、安装调试和试运行验收范围，容易把附加的信息化建设责任整体转嫁给供应商。"
                    ),
                    impact_on_competition_or_performance="可能将设备供货以外的接口开放、系统对接和持续配合义务一并压给供应商，抬高履约门槛并增加争议风险。",
                    legal_or_policy_basis="政府采购需求管理办法（财政部）；政府采购需求编制常见问题分析（中国政府采购网）",
                    rewrite_suggestion="建议将设备供货安装与医院信息系统接口开放、数据交换配合义务分开表述；如确需保留，应明确接口范围、配合边界、费用承担和验收责任。",
                    needs_human_review=True,
                    human_review_reason="需结合设备联网需求、医院现有信息系统接口边界和本次采购职责分工判断接口开放与持续配合义务是否应并入本次设备采购范围。",
                    finding_origin="analyzer",
                ),
            )
        if carbon_clauses:
            _append_theme_finding(
                findings,
                _build_theme_finding(
                    document=document,
                    clauses=carbon_clauses,
                    issue_type="template_mismatch",
                    problem_title="设备采购中叠加碳足迹盘查和持续改进义务，边界需复核",
                    risk_level="high",
                    severity_score=3,
                    confidence="high",
                    compliance_judgment="potentially_problematic",
                    why_it_is_risky=(
                        "文件在设备采购中要求中标人提供碳足迹盘查报告并持续提交改进报告。"
                        "这类 ESG 或碳管理义务通常不属于设备供货安装和验收的直接必需内容，容易把额外合规责任整体转嫁给供应商。"
                    ),
                    impact_on_competition_or_performance="可能将设备供货以外的碳管理和持续改进义务一并压给供应商，扩大履约边界并抬高投标成本。",
                    legal_or_policy_basis="政府采购需求管理办法（财政部）；政府采购需求编制常见问题分析（中国政府采购网）",
                    rewrite_suggestion="建议将设备供货安装与碳足迹盘查、持续改进报告义务分开表述；如确需保留，应单独说明业务必要性、适用范围和验收责任。",
                    needs_human_review=True,
                    human_review_reason="需结合采购人内部绿色采购管理要求、设备供货边界和碳管理职责分工判断相关义务是否应并入本次设备采购范围。",
                    finding_origin="analyzer",
                ),
            )
        if interface_clauses or carbon_clauses:
            return findings
        title = "设备采购场景叠加信息化接口和碳足迹义务，边界不清"
        rationale = (
            "文件在设备采购中叠加了软件端口开放、医院信息系统对接、数据交换费用承担以及碳足迹盘查和持续改进等义务。"
            "当设备供货、接口开发和碳足迹管理被一起写入同一采购范围时，容易导致采购边界不清，并把额外的信息化和 ESG 义务整体转嫁给供应商。"
        )
        impact = "可能将设备供货以外的信息系统接口建设和碳足迹管理义务一并压给供应商，抬高履约门槛并增加争议风险。"
        rewrite = "建议将设备供货、医院信息系统接口配合和碳足迹管理分开表述；与本次设备采购不直接相关的系统开放、持续对接和碳足迹报告义务应删除或单列采购。"
        review_reason = "需结合设备联网需求、医院现有信息系统接口边界和碳足迹管理职责判断相关义务是否应并入本次设备采购范围。"
    elif domain == "sports_facility_goods":
        mixed_markers = profile_out_of_scope_markers or profile_mixed_markers or ("二维码报修系统", "OTA远程升级", "智能显示", "远程升级")
        core_markers = profile_core_markers or ("运动场", "围网", "硅PU", "照明", "器材", "铺装")
        clauses = [
            clause
            for clause in document.clauses
            if is_effective_requirement_clause(clause)
            if any(marker in clause.text for marker in (*mixed_markers, *core_markers))
        ]
        out_of_scope_hits = _collect_marker_hits(clauses, mixed_markers)
        has_core_in_body = any(
            any(marker in clause.text for marker in core_markers) and not clause.text.startswith("项目名称")
            for clause in clauses
        )
        if len(out_of_scope_hits) < min_out_of_scope_hits or not has_core_in_body:
            return findings
        hard_hits = _collect_marker_hits(clauses, profile_hard_markers or mixed_markers)
        support_hits = _collect_marker_hits(clauses, profile_support_markers)
        support_clause_count = _count_marker_clauses(clauses, profile_support_markers)
        if not hard_hits and profile_support_markers and (len(support_hits) < 3 or support_clause_count < 2):
            return findings
        title = "体育器材及运动场设施叠加轻量智能化功能，边界需进一步论证"
        rationale = (
            "文件在体育器材及运动场设施采购中叠加了二维码报修、OTA远程升级、智能显示等轻量智能化功能。"
            "当器材供货、场地设施安装与数字化功能一并写入同一采购范围时，容易使采购边界从货物安装扩张到附加的信息化建设能力。"
        )
        impact = "可能把运动场器材供货安装以外的智能化支撑能力整体转化为履约要求或竞争门槛。"
        rewrite = "建议将体育器材及场地设施供货安装与轻量智能化功能分开表述；如确需保留，应说明业务必要性、边界和验收责任。"
        review_reason = "需结合项目是否仅为器材与场地设施建设，还是确需包含报修、升级和智能显示等数字化功能判断边界是否合理。"
    else:
        return findings
    if len(clauses) < 2:
        return findings
    _append_theme_finding(
        findings,
        _build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="template_mismatch",
            problem_title=title,
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=rationale,
            impact_on_competition_or_performance=impact,
            legal_or_policy_basis="政府采购需求管理办法（财政部）；政府采购需求编制常见问题分析（中国政府采购网）",
            rewrite_suggestion=rewrite,
            needs_human_review=True,
            human_review_reason=review_reason,
            finding_origin="analyzer",
        ),
    )
    return findings


def _collect_marker_hits(clauses, markers: tuple[str, ...]) -> tuple[str, ...]:
    hits: list[str] = []
    for clause in clauses:
        for marker in markers:
            if marker in clause.text:
                hits.append(marker)
    return tuple(dict.fromkeys(hits))


def _count_marker_clauses(clauses, markers: tuple[str, ...]) -> int:
    if not markers:
        return 0
    return sum(1 for clause in clauses if any(marker in clause.text for marker in markers))


def _prefer_dominant_commercial_section(clauses):
    if not clauses:
        return clauses
    counts: OrderedDict[str, int] = OrderedDict()
    for clause in clauses:
        key = _top_level_section_key(clause.section_path)
        counts[key] = counts.get(key, 0) + 1
    dominant_key, dominant_count = max(counts.items(), key=lambda item: item[1])
    if dominant_count < 3:
        return clauses
    preferred = [clause for clause in clauses if _top_level_section_key(clause.section_path) == dominant_key]
    return preferred or clauses


def _top_level_section_key(section_path: str | None) -> str:
    if not section_path:
        return ""
    return section_path.split("-")[0].strip()


def _add_template_domain_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("文件中存在与标的域不匹配的模板残留或义务外扩" in finding.problem_title for finding in findings):
        return findings
    domain = _effective_domain_key(document, classification)
    mismatch_markers = _domain_mismatch_markers(domain, classification=classification)
    template_scope_markers = catalog_template_scope_markers_for_classification(classification)
    mixed_scope_markers = ("软件端口", "医院信息系统", "HIS", "PACS", "LIS", "数据交换", "碳足迹", "盘查报告", "改进报告")
    clauses = []
    for clause in document.clauses:
        if _is_template_instruction_clause(clause):
            continue
        if _is_qualification_clause(clause):
            continue
        if not any(marker in clause.text for marker in mismatch_markers):
            continue
        scope_markers = template_scope_markers or ("保洁", "芯片", "系统", "安防", "设施维修", "特种设备", "垃圾", "实际需求为准", "平台", "接口", "软件")
        if not any(marker in clause.text for marker in scope_markers):
            continue
        if domain == "medical_device_goods" and any(marker in clause.text for marker in mixed_scope_markers):
            continue
        if domain == "furniture_goods" and not any(
            marker in clause.text for marker in ("资产定位", "定位管理标签模块", "蓝牙", "UWB", "资产管理读写基站", "智能芯片", "碳足迹", "无缝对接")
        ):
            continue
        if domain == "property_service":
            if _is_scoring_clause(clause):
                continue
            if not any(marker in clause.text for marker in ("芯片", "HIS", "PACS", "LIS", "数据交换", "软件著作权", "著作权登记证书", "实际需求为准")):
                continue
        if domain == "signage_printing_service":
            if _is_scoring_clause(clause):
                continue
            if not any(
                marker in clause.text
                for marker in ("成桥荷载试验", "交通部交工验收", "试验成果", "工程现场勘察", "试验人员", "试验仪器设备", "用户组织有关技术人员")
            ):
                continue
        clauses.append(clause)
    if len(clauses) < 1:
        return findings
    _append_theme_finding(
        findings,
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
        ),
    )
    return findings


def _effective_domain_key(
    document: NormalizedDocument,
    classification: CatalogClassification | None,
) -> str:
    if classification is not None and classification.primary_domain_key:
        return classification.primary_domain_key
    return _document_domain(document)


def _add_geographic_tendency_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("驻场、短时响应或服务场地要求形成事实上的属地倾斜" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "1小时",
                "1 小时",
                "60分钟",
                "60 分钟",
                "2小时",
                "2 小时",
                "4小时",
                "4 小时",
                "12小时内提供备件",
                "24小时内到场",
                "高新区内",
                "固定的售后服务场所",
                "驻场",
                "现场服务",
                "本地售后网点",
                "驻点服务站",
                "本地备件库",
            )
        )
        and (
            any(
                marker in clause.text
                for marker in (
                    "到场",
                    "响应",
                    "驻场",
                    "现场服务",
                    "售后服务场所",
                    "固定的售后服务场所",
                    "本地售后网点",
                    "驻点服务站",
                    "本地备件库",
                    "高新区内",
                )
            )
            or not any(marker in clause.text for marker in ("24小时营业", "24小时营业及就餐服务", "供餐服务", "就餐服务"))
        )
    ]
    if not clauses:
        return findings
    _append_theme_finding(
        findings,
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
        ),
    )
    return findings


def _add_acceptance_boundary_findings(document: NormalizedDocument, findings: list[Finding]) -> list[Finding]:
    if any("验收程序、复检与最终确认边界不清" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if _is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in ("验收报告", "最终验收结果", "复检", "技术验收", "商务验收", "开箱检验")
        )
    ]
    if not clauses:
        return findings
    _append_theme_finding(
        findings,
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
        ),
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
    _append_theme_finding(
        findings,
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
        ),
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
    _append_theme_finding(
        findings,
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
        ),
    )
    return findings


def _is_qualification_clause(clause) -> bool:
    if _is_template_instruction_clause(clause):
        return False
    text = " ".join(part for part in (clause.section_path or "", clause.source_section or "", clause.table_or_item_label or "") if part)
    if _is_scoring_clause(clause):
        return False
    return "资格" in text or "申请人的资格要求" in text


def _is_technical_clause(clause) -> bool:
    text = " ".join(part for part in (clause.section_path or "", clause.source_section or "") if part)
    return "技术要求" in text or "用户需求书" in text


def _is_commercial_clause(clause) -> bool:
    if _is_template_instruction_clause(clause):
        return False
    if _is_scoring_clause(clause):
        return False
    location_text = " ".join(part for part in (clause.section_path or "", clause.source_section or "") if part)
    text = " ".join(part for part in (location_text, clause.text or "") if part)
    strong_commercial_markers = ("付款", "支付", "验收", "履约评价", "评价标准", "评价指标", "扣款", "解除合同", "违约", "终验")
    if (
        _is_technical_clause(clause)
        and not any(marker in location_text for marker in ("商务要求", "合同条款", "违约责任", "付款方式", "验收条件"))
        and not any(marker in text for marker in strong_commercial_markers)
    ):
        return False
    return any(
        marker in text
        for marker in (
            "商务要求",
            "合同条款",
            "履约担保",
            "交货期限",
            "违约责任",
            "付款方式",
            "付款",
            "支付",
            "验收",
            "维修响应",
            "售后服务",
            "运输、安装",
            "评价标准",
            "评价指标",
            "解除合同",
            "扣款",
        )
    )


def _is_substantive_commercial_clause(clause) -> bool:
    if not _is_commercial_clause(clause):
        return False
    location_text = " ".join(part for part in (clause.section_path or "", clause.source_section or "", clause.table_or_item_label or "") if part)
    text = clause.text or ""
    if any(marker in location_text for marker in ("商务要求", "合同条款", "违约责任", "付款方式", "验收条件", "运输、安装")):
        return True
    if any(
        marker in text
        for marker in (
            "履约担保",
            "履约保证金",
            "售后服务保证金",
            "诚信履约备用金",
            "交货期限",
            "付款方式",
            "验收条件",
            "违约责任",
            "售后服务要求",
            "招标商务要求",
        )
    ):
        return True
    if any(marker in text for marker in ("履约评价", "评价标准", "评价指标")):
        return True
    if any(marker in text for marker in ("报验", "送检", "检测报告出具", "专家评审", "空气检测", "监理", "整改费用", "复验费用", "抽检费用")) and any(
        marker in text for marker in ("费用", "自行消化", "承担", "计入投标单价")
    ):
        return True
    marker_groups = (
        ("付款", "支付", "终验", "进度款", "预付款"),
        ("验收", "送检", "检测", "复检", "监理", "专家评审"),
        ("24小时", "1 小时", "48小时", "解除合同", "终止合同", "扣款金额", "损失", "承担", "违约金", "到场"),
    )
    matched_groups = sum(1 for group in marker_groups if any(marker in text for marker in group))
    return matched_groups >= 2


def _is_template_instruction_clause(clause) -> bool:
    return not is_effective_requirement_clause(clause)


def _is_explanatory_summary_clause(clause) -> bool:
    text = clause.text or ""
    if len(text) < 80:
        return False
    return (
        any(marker in text for marker in ("包括但不限于", "包括不不限于", "借助自身的", "对项目提供支撑", "高质量的服务要求"))
        and sum(text.count(marker) for marker in ("；", "。", "：", "1.", "2.", "3.", "4.", "①", "②", "③", "④")) >= 5
    )


def _domain_mismatch_markers(domain: str, classification: CatalogClassification | None = None) -> tuple[str, ...]:
    mapping = {
        "information_system": ("园区保洁", "设施维修", "安防管理", "保洁", "垃圾", "特种设备", "高空清洗", "CCRC", "ISO20000"),
        "property_service": ("芯片", "系统", "软件", "平台", "接口", "HIS", "PACS", "LIS", "数据交换", "棉花加工", "水运工程监理甲级"),
        "signage_printing_service": (
            "IT服务管理体系认证",
            "保安服务认证",
            "信息安全管理体系认证",
            "学生饮用奶定点生产企业资格",
            "成桥荷载试验",
            "交通部交工验收",
            "试验成果",
            "工程现场勘察",
            "试验人员",
        ),
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
        "medical_device_goods": (
            "高空清洗",
            "绿色物业管理评价标识",
            "软件端口",
            "医院信息系统",
            "HIS",
            "PACS",
            "LIS",
            "碳足迹",
            "生活垃圾分类",
            "企业诚信管理体系",
        ),
        "equipment_installation": ("有害生物防制", "SPCA", "有机产品认证", "水运机电工程专项监理", "水运工程监理甲级"),
        "general": ("园区保洁", "设施维修", "安防管理", "保洁", "芯片", "系统", "特种设备", "有害生物防制", "SPCA", "高空清洗", "CCRC", "ISO20000", "水运工程监理甲级", "棉花加工"),
        "furniture_goods": ("资产定位", "定位管理标签模块", "蓝牙", "UWB", "资产管理读写基站", "智能芯片", "碳足迹", "无缝对接"),
    }
    markers = list(mapping.get(domain, mapping["general"]))
    markers.extend(catalog_domain_mismatch_markers_for_classification(classification))
    if classification_has_catalog_prefix(classification, "C160"):
        markers.extend(("软件", "平台", "接口", "软件著作权"))
    if classification_has_catalog_prefix(classification, "C2307") or classification_has_catalog_prefix(classification, "C2309"):
        markers.extend(("宣传", "印刷", "广告", "导视"))
    if classification_has_catalog_prefix(classification, "A0702") or classification_has_catalog_prefix(classification, "A023103"):
        markers.extend(("配方颗粒", "药瓶清洁", "自动化调剂"))
    if classification_has_catalog_prefix(classification, "B0608"):
        markers.extend(("安装调试", "机电设备", "运行期"))
    return tuple(dict.fromkeys(markers))


def _is_scoring_clause(clause) -> bool:
    if _is_template_instruction_clause(clause):
        return False
    section_path = clause.section_path or ""
    source_section = clause.source_section or ""
    table_label = clause.table_or_item_label or ""
    text = clause.text or ""
    return (
        "评标信息" in section_path
        or "评分" in section_path
        or "评分" in source_section
        or "评分" in table_label
        or any(marker in text for marker in ("技术部分评分", "商务部分评分", "价格部分评分", "评分PT", "评分PB", "评审项"))
    )


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
) -> Finding | None:
    ordered = sorted(clauses, key=lambda clause: (clause.line_start, clause.line_end))
    ordered = filter_effective_requirement_clauses(ordered)
    if not ordered:
        return None
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


def _append_theme_finding(findings: list[Finding], candidate: Finding | None) -> None:
    if candidate is not None:
        findings.append(candidate)


def _apply_theme_splitter_and_summarizer(
    findings: list[Finding],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    for finding in findings:
        if finding.finding_origin != "analyzer":
            continue
        finding.source_text = _build_theme_excerpt(finding.source_text)
        if finding.problem_title == "认证评分混入错位证书且高分值结构失衡":
            finding.why_it_is_risky = (
                "认证评分同时混入企业称号、跨领域证书和高权重认证项。"
                "这类内容不仅与项目供货和售后履约关联较弱，还会通过高分值结构放大无关材料的竞争优势。"
            )
            finding.rewrite_suggestion = (
                "建议将企业称号、跨领域证书和体系认证拆开审视，仅保留与质量控制和售后履约直接相关的少量辅助性证明，并整体压降分值。"
            )
        if finding.problem_title == "认证评分项目过密且高分值集中":
            finding.why_it_is_risky = (
                "评分表对体系认证、低VOCs、家具有害物质限量、抗菌和防霉等多类认证连续赋予高分。"
                "即使这些认证与家具场景存在一定关联，过密设置并叠加高分值，也会使认证储备对中标结果产生过强影响。"
            )
            finding.rewrite_suggestion = (
                "建议压降认证类总分值，避免连续设置多项高分认证；仅保留与家具质量控制和环保安全直接相关的少量辅助性证明，并取消中标后补证安排。"
            )
        if finding.problem_title == "生产设备和制造能力直接高分赋值且与核心履约评价边界不清":
            finding.why_it_is_risky = (
                "评分项直接按生产设备和制造线储备给予高分，并通过购买合同、租赁合同和发票逐项取证。"
                "这会把企业既有设备规模放大为高分优势，弱化对家具供货质量、安装组织和售后保障能力的评价。"
            )
            finding.rewrite_suggestion = (
                "建议删除按生产设备清单逐项赋高分的设计，改为围绕供货保障、交付计划、安装组织和质量控制能力设置低权重、可核验的评分因素。"
            )
        if finding.problem_title == "样品评分叠加递交签到和不接收机制形成额外门槛":
            finding.why_it_is_risky = (
                "样品评分本身权重较高，同时又要求投标人在固定时段和固定地点完成样品签到，未签到即不予接收样品。"
                "这会把现场组织条件和短时递交能力叠加转化为得分前提，形成额外竞争门槛。"
            )
            finding.rewrite_suggestion = (
                "建议压降样品评分权重，简化样品递交和签到要求，不宜将固定时段签到和不接收机制直接叠加为高分项前置条件。"
            )
        if finding.problem_title == "售后服务评分混入业绩、荣誉和资格材料":
            finding.rewrite_suggestion = (
                "建议删除售后服务评分中的医疗行业业绩、守合同重信用、科技型中小企业和营业执照等加分，仅保留与售后人员、响应机制、备件保障和培训方案直接相关的评分因素。"
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
            if "核心履约能力" not in finding.why_it_is_risky:
                finding.why_it_is_risky = (
                    "评分项名称、评分内容和评分证据之间没有保持一致，导致方案项、商务项或认证项中混入无关案例、证明形式和企业属性。"
                    "这会让评审重心从履约能力偏向材料包装和取证形式。"
                )
            if "核心交付、实施组织和履约保障能力" not in finding.rewrite_suggestion:
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
        finding.source_text = _select_representative_evidence(finding, classification=classification)
    return findings


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
