from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from agent_compliance.knowledge.catalog_knowledge_profile import catalog_knowledge_profiles_for_classification
from agent_compliance.knowledge.procurement_catalog import CatalogClassification, classify_procurement_catalog, load_procurement_catalogs
from agent_compliance.pipelines.procurement_stage_router import ProcurementStageProfile, route_procurement_stage
from agent_compliance.schemas import Finding, NormalizedDocument


@dataclass
class DocumentRiskProfile:
    dominant_sections: tuple[str, ...]
    dominant_issue_types: tuple[str, ...]
    dominant_theme_titles: tuple[str, ...]
    high_risk_count: int
    medium_risk_count: int


@dataclass
class DocumentStrategyProfile:
    procurement_stage_key: str
    procurement_stage_name: str
    procurement_stage_goal: str
    procurement_stage_posture: str
    procurement_stage_output_bias: tuple[str, ...]
    procurement_mode: str
    domain_hint: str
    primary_focus: tuple[str, ...]
    review_route: tuple[str, ...]
    primary_catalog_id: str = ""
    primary_catalog_name: str = ""
    secondary_catalog_names: tuple[str, ...] = ()
    primary_mapped_catalog_codes: tuple[str, ...] = ()
    secondary_mapped_catalog_codes: tuple[str, ...] = ()
    is_mixed_scope: bool = False
    catalog_confidence: float = 0.0
    catalog_evidence: tuple[str, ...] = ()
    preferred_analyzer_groups: tuple[str, ...] = ()
    catalog_reasonable_requirements: tuple[str, ...] = ()
    catalog_high_risk_patterns: tuple[str, ...] = ()
    catalog_boundary_notes: tuple[str, ...] = ()


def build_overall_summary(
    findings: list[Finding],
    document: NormalizedDocument | None = None,
    classification: CatalogClassification | None = None,
) -> str:
    profile = build_document_risk_profile(findings)
    strategy = build_document_strategy_profile(findings, document=document, classification=classification)
    high = sum(1 for finding in findings if finding.risk_level == "high")
    medium = sum(1 for finding in findings if finding.risk_level == "medium")
    summary = (
        f"本地离线审查共形成 {len(findings)} 条去重 findings，其中高风险 {high} 条、中风险 {medium} 条。"
        " 当前结果已接入本地规则映射和引用资料检索，可作为正式审查前的离线初筛与复审输入。"
    )
    if strategy.procurement_stage_name:
        summary += f" 当前审查阶段定位为{strategy.procurement_stage_name}。"
    if strategy.procurement_mode:
        summary += f" 当前文件识别为{strategy.procurement_mode}，主标的提示为{strategy.domain_hint}。"
    if strategy.primary_catalog_name:
        summary += f" 当前主品目识别为{strategy.primary_catalog_name}。"
    if strategy.primary_mapped_catalog_codes:
        summary += f" 对应官方品目编码包括{join_labels(strategy.primary_mapped_catalog_codes)}。"
    if strategy.secondary_catalog_names:
        summary += f" 次品目提示包括{join_labels(strategy.secondary_catalog_names)}。"
    if strategy.secondary_mapped_catalog_codes:
        summary += f" 次品目映射编码包括{join_labels(strategy.secondary_mapped_catalog_codes[:4])}。"
    if strategy.is_mixed_scope:
        summary += " 当前识别为混合采购场景，需重点复核边界不清、义务外扩和错位要求。"
    if strategy.catalog_high_risk_patterns:
        summary += f" 按当前品目画像，需重点留意{join_labels(strategy.catalog_high_risk_patterns[:3])}。"
    if profile.dominant_sections:
        summary += f" 该文件的主风险重心集中在{join_labels(profile.dominant_sections)}。"
    if profile.dominant_theme_titles:
        summary += f" 当前最突出的主问题包括：{join_labels(profile.dominant_theme_titles)}。"
    if strategy.review_route:
        summary += f" 建议优先按“{' -> '.join(strategy.review_route)}”的顺序理解和复核本文件。"
    return summary


def build_document_risk_profile(findings: list[Finding]) -> DocumentRiskProfile:
    if not findings:
        return DocumentRiskProfile((), (), (), 0, 0)

    weighted_findings = [finding for finding in findings if finding.risk_level in {"high", "medium"}]
    candidates = weighted_findings or findings

    section_scores: "OrderedDict[str, int]" = OrderedDict()
    issue_scores: "OrderedDict[str, int]" = OrderedDict()
    theme_titles: list[str] = []
    for finding in candidates:
        weight = 2 if finding.risk_level == "high" else 1
        section = section_key_from_finding(finding)
        section_scores[section] = section_scores.get(section, 0) + weight
        issue_scores[finding.issue_type] = issue_scores.get(finding.issue_type, 0) + weight
        if finding.finding_origin == "analyzer" and finding.problem_title not in theme_titles:
            theme_titles.append(finding.problem_title)

    dominant_sections = tuple(
        section_label_from_key(section)
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


def build_document_strategy_profile(
    findings: list[Finding],
    document: NormalizedDocument | None = None,
    classification: CatalogClassification | None = None,
) -> DocumentStrategyProfile:
    classification = classification or (classify_procurement_catalog(document) if document is not None else None)
    stage_profile = route_procurement_stage(document=document, findings=findings)
    if not findings:
        domain = classification.primary_domain_key if classification is not None else "general"
        procurement_mode = "综合型政府采购项目"
        domain_hint = "需结合全部章节综合判断"
        if domain == "medical_tcm_mixed":
            procurement_mode = "医疗药品或医用配套采购项目"
            domain_hint = "药品供货、设备配套与院内接口并存"
        elif domain == "medical_tcm":
            procurement_mode = "医疗药品或医用配套采购项目"
            domain_hint = "药品供货与医用配套服务类"
        elif domain == "sports_facility_goods":
            procurement_mode = "体育器材供货并含运动场设施安装项目"
            domain_hint = "运动场器材、围网照明、场地面层与轻量智能化功能并存"
        elif domain == "information_system":
            procurement_mode = "信息化或数字化服务项目"
            domain_hint = "平台建设、系统对接或持续运维类"
        return DocumentStrategyProfile(
            procurement_stage_key=stage_profile.stage_key,
            procurement_stage_name=stage_profile.stage_name,
            procurement_stage_goal=stage_profile.stage_goal,
            procurement_stage_posture=stage_profile.review_posture,
            procurement_stage_output_bias=stage_profile.output_bias,
            procurement_mode=procurement_mode,
            domain_hint=domain_hint,
            primary_focus=("综合条款",),
            review_route=("综合条款", "文件级风险画像"),
            primary_catalog_id=classification.primary_catalog if classification else "",
            primary_catalog_name=classification.primary_catalog_name if classification else "",
            secondary_catalog_names=classification.secondary_catalog_names if classification else (),
            primary_mapped_catalog_codes=classification.primary_mapped_catalog_codes if classification else (),
            secondary_mapped_catalog_codes=classification.secondary_mapped_catalog_codes if classification else (),
            is_mixed_scope=classification.is_mixed_scope if classification else False,
            catalog_confidence=classification.catalog_confidence if classification else 0.0,
            catalog_evidence=classification.catalog_evidence if classification else (),
            preferred_analyzer_groups=preferred_analyzer_groups_for_classification(classification),
            catalog_reasonable_requirements=_catalog_reasonable_requirements_for_classification(classification),
            catalog_high_risk_patterns=_catalog_high_risk_patterns_for_classification(classification),
            catalog_boundary_notes=_catalog_boundary_notes_for_classification(classification),
        )

    section_scores: dict[str, int] = {}
    for finding in findings:
        section = section_key_from_finding(finding)
        weight = 2 if finding.risk_level == "high" else 1
        section_scores[section] = section_scores.get(section, 0) + weight
    ordered_sections = [section for section, _ in sorted(section_scores.items(), key=lambda item: (-item[1], item[0]))]

    domain = classification.primary_domain_key if classification is not None else "general"
    combined = " ".join(
        filter(
            None,
            [
                *[finding.problem_title for finding in findings],
                *[finding.source_text for finding in findings if finding.source_text],
            ],
        )
    )

    if domain == "furniture_goods":
        procurement_mode = "货物采购并含安装调试项目"
        domain_hint = "办公或医用家具供货、安装和售后保障类"
    elif domain == "textile_goods":
        procurement_mode = "货物采购并含安装调试项目"
        domain_hint = "窗帘、隔帘、床品或被服供货、安装和售后保障类"
    elif domain == "catering_service":
        procurement_mode = "餐饮托管或食堂运营服务项目"
        domain_hint = "医院、学校或公共机构食堂托管、供餐保障与后勤餐饮服务类"
    elif domain == "property_service":
        procurement_mode = "物业管理或综合后勤服务项目"
        domain_hint = "校园、医院或公共机构物业服务及驻场保障类"
    elif domain == "signage_printing_service":
        procurement_mode = "标识标牌及宣传印制综合服务项目"
        domain_hint = "医院、学校或公共机构标识导视、宣传印制和现场制作安装维护类"
    elif domain == "sports_facility_goods":
        procurement_mode = "体育器材供货并含运动场设施安装项目"
        domain_hint = "运动场器材、围网照明、场地面层与轻量智能化功能并存"
    elif any(token in combined for token in ("血透", "透析", "医疗器械", "设备采购", "HIS", "PACS", "LIS", "碳足迹")) or domain == "medical_device_goods":
        procurement_mode = "货物采购并含安装调试项目"
        domain_hint = "医用设备供货、院内接口配套与附加合规义务并存"
    elif any(token in combined for token in ("中药", "药品", "颗粒", "医院")) or domain in {"medical_tcm", "medical_tcm_mixed"}:
        procurement_mode = "医疗药品或医用配套采购项目"
        domain_hint = "药品供货、设备配套与院内接口并存" if domain == "medical_tcm_mixed" else "药品供货与医用配套服务类"
    elif any(token in combined for token in ("系统", "平台", "接口", "演示", "驻场运维")) or domain == "information_system":
        procurement_mode = "信息化或数字化服务项目"
        domain_hint = "平台建设、系统对接或持续运维类"
    elif any(token in combined for token in ("发电机", "机电设备", "安装调试")) or domain == "equipment_installation":
        procurement_mode = "货物采购并含安装调试项目"
        domain_hint = "设备供货与安装验收并行"
    else:
        procurement_mode = "综合型政府采购项目"
        domain_hint = "需结合资格、评分、技术和商务主问题综合判断"

    focus_mapping = {
        "qualification": "资格条件",
        "scoring": "评分标准",
        "technical": "技术要求",
        "commercial": "商务与验收",
        "other": "综合条款",
    }
    primary_focus = tuple(focus_mapping.get(section, "综合条款") for section in ordered_sections[:3]) or ("综合条款",)
    review_route = tuple(dict.fromkeys([*primary_focus, "文件级风险画像"]))

    return DocumentStrategyProfile(
        procurement_stage_key=stage_profile.stage_key,
        procurement_stage_name=stage_profile.stage_name,
        procurement_stage_goal=stage_profile.stage_goal,
        procurement_stage_posture=stage_profile.review_posture,
        procurement_stage_output_bias=stage_profile.output_bias,
        procurement_mode=procurement_mode,
        domain_hint=domain_hint,
        primary_focus=primary_focus,
        review_route=review_route,
        primary_catalog_id=classification.primary_catalog if classification else "",
        primary_catalog_name=classification.primary_catalog_name if classification else "",
        secondary_catalog_names=classification.secondary_catalog_names if classification else (),
        primary_mapped_catalog_codes=classification.primary_mapped_catalog_codes if classification else (),
        secondary_mapped_catalog_codes=classification.secondary_mapped_catalog_codes if classification else (),
        is_mixed_scope=classification.is_mixed_scope if classification else False,
        catalog_confidence=classification.catalog_confidence if classification else 0.0,
        catalog_evidence=classification.catalog_evidence if classification else (),
        preferred_analyzer_groups=preferred_analyzer_groups_for_classification(classification),
        catalog_reasonable_requirements=_catalog_reasonable_requirements_for_classification(classification),
        catalog_high_risk_patterns=_catalog_high_risk_patterns_for_classification(classification),
        catalog_boundary_notes=_catalog_boundary_notes_for_classification(classification),
    )


def join_labels(values: tuple[str, ...]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]}和{values[1]}"
    return f"{'、'.join(values[:-1])}和{values[-1]}"


def section_key_from_finding(finding: Finding) -> str:
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


def section_label_from_key(section_key: str) -> str:
    mapping = {
        "qualification": "资格条件",
        "scoring": "评分标准",
        "technical": "技术要求",
        "commercial": "商务与验收",
    }
    return mapping.get(section_key, "综合问题")


def document_domain(document: NormalizedDocument) -> str:
    return classify_procurement_catalog(document).primary_domain_key


def build_analyzer_execution_order(
    findings: list[Finding],
    document: NormalizedDocument | None = None,
    classification: CatalogClassification | None = None,
) -> tuple[str, ...]:
    strategy = build_document_strategy_profile(findings, document=document, classification=classification)
    focus_to_group = {
        "资格条件": "qualification",
        "评分标准": "scoring",
        "技术要求": "technical",
        "商务与验收": "commercial",
        "综合条款": "commercial",
    }
    ordered_groups: list[str] = []
    for group in strategy.preferred_analyzer_groups:
        if group not in ordered_groups:
            ordered_groups.append(group)
    for focus in strategy.primary_focus:
        group = focus_to_group.get(focus)
        if group and group not in ordered_groups:
            ordered_groups.append(group)
    for group in ("qualification", "scoring", "technical", "commercial"):
        if group not in ordered_groups:
            ordered_groups.append(group)
    return tuple(ordered_groups)


def preferred_analyzer_groups_for_classification(classification: CatalogClassification | None) -> tuple[str, ...]:
    if classification is None or not classification.primary_catalog:
        return ()
    analyzer_names: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        analyzer_names.extend(profile.preferred_analyzers)
    if not analyzer_names:
        catalogs = {catalog.catalog_id: catalog for catalog in load_procurement_catalogs()}
        primary = catalogs.get(classification.primary_catalog)
        if primary is not None:
            analyzer_names.extend(primary.preferred_analyzers)
        for catalog_id in classification.secondary_catalogs:
            catalog = catalogs.get(catalog_id)
            if catalog is not None:
                analyzer_names.extend(catalog.preferred_analyzers)

    mapped_groups: list[str] = []
    for analyzer_name in analyzer_names:
        group = analyzer_group_for_name(analyzer_name)
        if group and group not in mapped_groups:
            mapped_groups.append(group)
    return tuple(mapped_groups)


def analyzer_group_for_name(analyzer_name: str) -> str | None:
    if analyzer_name.startswith("qualification_"):
        return "qualification"
    if analyzer_name.startswith(("brand_", "scoring_", "demo_", "personnel_")):
        return "scoring"
    if analyzer_name.startswith(("technical_", "mixed_scope_")):
        return "technical"
    if analyzer_name.startswith(("commercial_", "geographic_", "acceptance_", "liability_", "proof_")):
        return "commercial"
    return None


def _catalog_reasonable_requirements_for_classification(classification: CatalogClassification | None) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.reasonable_requirements)
    return tuple(dict.fromkeys(values))


def _catalog_high_risk_patterns_for_classification(classification: CatalogClassification | None) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.high_risk_patterns)
    return tuple(dict.fromkeys(values))


def _catalog_boundary_notes_for_classification(classification: CatalogClassification | None) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        if profile.boundary_notes:
            values.append(profile.boundary_notes)
    return tuple(dict.fromkeys(values))
