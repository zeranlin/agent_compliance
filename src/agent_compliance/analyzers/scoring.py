from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Callable

from agent_compliance.knowledge.procurement_catalog import CatalogClassification, classification_has_domain
from agent_compliance.schemas import Finding, NormalizedDocument


ClausePredicate = Callable[[Any], bool]
ThemeBuilder = Callable[..., Finding]
DomainResolver = Callable[[NormalizedDocument], str]
TextMerger = Callable[..., str | None]


def apply_scoring_analyzers(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
    document_domain: DomainResolver,
    merge_optional_text: TextMerger,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    findings = _add_scoring_structure_imbalance_finding(findings, merge_optional_text=merge_optional_text)
    findings = _add_goods_capacity_scoring_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_scoring_clause=is_scoring_clause,
        document_domain=document_domain,
        catalog_classification=catalog_classification,
    )
    findings = _add_furniture_production_capacity_scoring_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_scoring_clause=is_scoring_clause,
        document_domain=document_domain,
        catalog_classification=catalog_classification,
    )
    findings = _add_subjective_scoring_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_demo_mechanism_theme_finding(document, findings, build_theme_finding=build_theme_finding)
    findings = _add_sample_submission_barrier_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_personnel_scoring_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_business_strength_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_scoring_semantic_consistency_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_service_scoring_mismatch_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_warranty_extension_scoring_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_software_copyright_scoring_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_experience_evaluation_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_property_service_experience_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_scoring_clause=is_scoring_clause,
        document_domain=document_domain,
        catalog_classification=catalog_classification,
    )
    findings = _add_brand_and_certification_scoring_findings(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_scoring_clause=is_scoring_clause,
        document_domain=document_domain,
        catalog_classification=catalog_classification,
    )
    return findings


def _add_goods_capacity_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
    document_domain: DomainResolver,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("经验评价、生产设备和认证因素高分集中并偏离核心供货能力" in finding.problem_title for finding in findings):
        return findings
    if not _matches_catalog_domain(document, document_domain, catalog_classification, "furniture_goods"):
        return findings
    scoring_clauses = [clause for clause in document.clauses if is_scoring_clause(clause)]
    category_clauses = [
        clause
        for clause in scoring_clauses
        if any(marker in clause.text for marker in ("经验评价", "生产设备情况", "相关认证情况"))
    ]
    if len(category_clauses) < 2:
        return findings
    weighted_clauses = [
        clause
        for clause in scoring_clauses
        if any(
            marker in clause.text
            for marker in (
                "最高得100分",
                "最高得 100 分",
                "每提供一项得50分",
                "每提供一项得 50 分",
                "每具有以上一种相关设备的得10分",
                "每具有以上一种相关设备的得 10 分",
                "累计得分，最高得100分",
                "累计得分，最高得 100 分",
            )
        )
    ]
    if not weighted_clauses:
        return findings
    clauses_by_line: "OrderedDict[int, Any]" = OrderedDict()
    for clause in [*category_clauses, *weighted_clauses]:
        clauses_by_line.setdefault(clause.line_start, clause)
    clauses = list(clauses_by_line.values())
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_structure_imbalance",
            problem_title="经验评价、生产设备和认证因素高分集中并偏离核心供货能力",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分表将经验评价、生产设备储备和多项认证集中设置为高分项，且单项累计分值明显偏高。"
                "这类设计会把企业既有规模、设备和认证储备放大为决定性优势，弱化对家具供货质量、安装组织和售后履约能力的评价。"
            ),
            impact_on_competition_or_performance="可能使评分重心偏离家具供货、安装和售后保障等核心履约能力，对既有资源更强的供应商形成明显倾斜。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议压降经验评价、生产设备和认证总分值，改为围绕家具供货质量、安装组织、交付计划和售后保障设置更直接的可核验评分因素。",
            needs_human_review=True,
            human_review_reason="需结合家具项目的供货、安装和售后履约重点判断经验、设备和认证因素是否被不当放大为高分竞争优势。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_furniture_production_capacity_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
    document_domain: DomainResolver,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("生产设备和制造能力直接高分赋值且与核心履约评价边界不清" in finding.problem_title for finding in findings):
        return findings
    if not _matches_catalog_domain(document, document_domain, catalog_classification, "furniture_goods"):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("生产设备", "数控剪板机", "自动化生产线", "异性海绵切割机", "购买发票", "租赁设备"))
        and any(marker in clause.text for marker in ("每提供一项得10分", "最高得100分", "最高得 100 分"))
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="生产设备和制造能力直接高分赋值且与核心履约评价边界不清",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分项直接按生产设备和制造线储备给予高分，并通过购买合同、租赁合同和发票等材料逐项计分。"
                "这类设计会把企业既有设备规模直接转化为高分优势，弱化对家具供货质量、安装组织和售后保障能力的评价。"
            ),
            impact_on_competition_or_performance="可能显著放大既有制造设备储备的竞争优势，使评分重心偏离本项目实际交付和安装履约能力。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议删除按生产设备清单逐项赋高分的设计，改为围绕供货保障、交付计划、安装组织和质量控制能力设置低权重、可核验的评分因素。",
            needs_human_review=True,
            human_review_reason="需结合家具供货项目的实际履约重点判断生产设备和制造能力是否被不当放大为决定性高分因素。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_scoring_structure_imbalance_finding(
    findings: list[Finding],
    *,
    merge_optional_text: TextMerger,
) -> list[Finding]:
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
        page_hint=merge_optional_text((finding.page_hint for finding in source_findings), separator=" / "),
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
        legal_or_policy_basis=merge_optional_text(
            (finding.legal_or_policy_basis for finding in source_findings if finding.legal_or_policy_basis)
        ),
        rewrite_suggestion="建议对样品、认证、业绩等非价格因素重新分配权重，压降单类高分项，并将评分拆解为与履约直接相关的多个可核验指标。",
        needs_human_review=False,
        human_review_reason=None,
    )
    return [*findings, aggregate]


def _add_subjective_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("多个方案评分项大量使用主观分档" in finding.problem_title for finding in findings):
        return findings
    candidates = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("评审为优", "评审为良", "评审为中", "评审为差", "方案极合理", "条理极清晰", "可操作性极强"))
    ]
    high_weight_candidates = [
        clause
        for clause in candidates
        if any(marker in clause.text for marker in ("70 分", "70分", "60 分", "60分", "40 分", "40分"))
    ]
    if len(candidates) < 3 and not (len(candidates) >= 2 and len(high_weight_candidates) >= 2):
        return findings
    findings.append(
        build_theme_finding(
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


def _add_demo_mechanism_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
) -> list[Finding]:
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
        build_theme_finding(
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


def _add_sample_submission_barrier_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("样品评分叠加递交签到和不接收机制形成额外门槛" in finding.problem_title for finding in findings):
        return findings
    sample_scoring_clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("样品", "样品清单", "样品不得3D打印", "评审为优", "材质、外观、工艺"))
    ]
    sign_in_clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "样品递交签到",
                "不予签到",
                "样品不予接收",
                "签到时间截止后",
                "未进行签到",
                "授权委托书",
                "签到地点",
            )
        )
    ]
    if not sample_scoring_clauses or not sign_in_clauses:
        return findings
    clauses = [*sample_scoring_clauses[:4], *sign_in_clauses[:4]]
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_structure_imbalance",
            problem_title="样品评分叠加递交签到和不接收机制形成额外门槛",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "样品评分本身权重较高，同时又要求投标人在固定时段和固定地点完成样品签到，未签到即不予接收样品。"
                "这会把现场组织条件和短时递交能力叠加转化为得分前提，形成额外竞争门槛。"
            ),
            impact_on_competition_or_performance="可能对非本地或现场组织能力较弱的供应商形成明显不利影响。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议压降样品评分权重，简化样品递交和签到要求，不宜将固定时段签到和不接收机制直接叠加为高分项前置条件。",
            needs_human_review=True,
            human_review_reason="需结合样品评审必要性、样品体积和递交组织方式判断签到和不接收机制是否构成额外竞争门槛。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_personnel_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("人员与团队评分混入错位证书并过度堆叠条件" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "学历",
                "学位",
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
                "高级餐饮业职业经理人",
                "食品安全管理员",
                "中式烹调师",
                "中式（西式）面点师",
                "中式烹调师或中式（西式）面点师",
                "健康证明",
            )
        )
    ]
    catering_personnel_markers = (
        "高级餐饮业职业经理人",
        "食品安全管理员",
        "中式烹调师",
        "中式（西式）面点师",
        "中式烹调师或中式（西式）面点师",
    )
    if len(clauses) < 2 and not any(any(marker in clause.text for marker in catering_personnel_markers) for clause in clauses):
        return findings
    findings.append(
        build_theme_finding(
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
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("商务评分将企业背景和一般财务能力直接转化为高分优势" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("注册资本", "营业收入", "净利润", "国家相关标准委员会", "国家标准", "行业标准"))
    ]
    if len(clauses) < 3:
        return findings
    findings.append(
        build_theme_finding(
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
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("评分项名称、内容和评分证据之间不一致" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "工程案例",
                "CMA",
                "检测报告",
                "IT服务管理体系认证",
                "保安服务认证",
                "信息安全管理体系认证",
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
                "定位管理标签模块",
                "软件著作权",
                "专利证书",
                "资产管理读写基站",
                "先进单位",
                "注册安全工程师",
                "食品安全责任险",
                "公众责任险",
                "高级餐饮业职业经理人",
                "食品安全管理员",
            )
        )
    ]
    category_markers = {
        "report_formality": ("CMA", "检测报告"),
        "business_background": ("资产总额", "成立时间", "营业收入", "净利润", "科技型中小企业"),
        "cross_domain": (
            "高空清洗",
            "CCRC",
            "ISO20000",
            "有机产品认证",
            "生活垃圾分类",
            "先进单位",
            "注册安全工程师",
            "IT服务管理体系认证",
            "保安服务认证",
            "信息安全管理体系认证",
        ),
        "ip_or_system": ("定位管理标签模块", "软件著作权", "专利证书", "资产管理读写基站"),
        "insurance_or_personnel": ("食品安全责任险", "公众责任险", "高级餐饮业职业经理人", "食品安全管理员"),
    }
    hit_categories = {
        category
        for category, markers in category_markers.items()
        if any(any(marker in clause.text for marker in markers) for clause in clauses)
    }
    if len(clauses) < 2 or len(hit_categories) < 2:
        return findings
    findings.append(
        build_theme_finding(
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


def _add_service_scoring_mismatch_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any(
        finding.problem_title in {"售后服务评分混入荣誉证书且主观分值偏高", "售后服务评分混入业绩、荣誉和资格材料"}
        for finding in findings
    ):
        return findings
    has_service_scoring_context = any(
        is_scoring_clause(clause)
        and any(marker in f"{clause.section_path or ''} {clause.text}" for marker in ("售后服务", "产品维护服务", "产品培训方案", "备品备件", "产品配件价格优惠"))
        for clause in document.clauses
    )
    service_content_clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("医疗行业", "守合同重信用", "科技型中小企业", "营业执照", "事业单位法人证书"))
    ]
    if has_service_scoring_context and len(service_content_clauses) >= 2:
        findings.append(
            build_theme_finding(
                document=document,
                clauses=service_content_clauses,
                issue_type="scoring_content_mismatch",
                problem_title="售后服务评分混入业绩、荣誉和资格材料",
                risk_level="high",
                severity_score=3,
                confidence="high",
                compliance_judgment="likely_non_compliant",
                why_it_is_risky=(
                    "售后服务评分项中混入了医疗行业业绩、守合同重信用称号、科技型中小企业证明以及营业执照等资格材料。"
                    "这会把与售后服务方案主题关联不足的企业背景和资格证明直接转化为高分优势。"
                ),
                impact_on_competition_or_performance="可能让售后服务评分偏离响应机制、备件保障和培训方案等核心履约能力，放大无关材料的竞争影响。",
                legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
                rewrite_suggestion="建议删除售后服务评分中的业绩、企业荣誉和资格证明加分，仅围绕售后团队、响应机制、备件保障和培训安排评分。",
                needs_human_review=False,
                human_review_reason=None,
                finding_origin="analyzer",
            )
        )
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in f"{clause.section_path or ''} {clause.text}" for marker in ("售后服务方案", "产品升级", "配品配件", "服务保障"))
        and any(marker in clause.text for marker in ("先进单位", "注册安全工程师", "方案极合理", "70 分", "70分"))
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="售后服务评分混入荣誉证书且主观分值偏高",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "售后服务评分一方面考察服务保障、升级维护和配件方案，另一方面又叠加“先进单位”荣誉和注册安全工程师证书，并辅以较高分值的主观分档。"
                "这会把与售后履约主题关联不足的荣誉和证书直接转化为高分优势。"
            ),
            impact_on_competition_or_performance="可能将售后服务方案评分从履约保障能力评价偏移到荣誉和证书堆叠，放大非关键材料的竞争影响。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；奖项荣誉信用等级评分问题（中国政府采购网）",
            rewrite_suggestion="建议删除售后服务评分中与服务主题不一致的荣誉和证书要求，压降主观分档权重，仅围绕响应机制、升级维护、备件保障和服务组织评分。",
            needs_human_review=True,
            human_review_reason="需结合设备售后服务组织方式判断注册安全工程师和先进单位荣誉是否与本项目售后履约能力直接相关。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_warranty_extension_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("免费质保期延长按年度直接高分赋值" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and "免费质保期" in clause.text
        and any(marker in clause.text for marker in ("每延长1年", "每延长 1 年", "得100分", "最高100分", "最高得100分"))
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_scoring_weight",
            problem_title="免费质保期延长按年度直接高分赋值",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分项在满足基础商务要求的前提下，又按免费质保期每延长 1 年直接给予 100 分。"
                "这类设计会把单一售后承诺放大为决定性高分因素，导致评分结构明显失衡。"
            ),
            impact_on_competition_or_performance="可能显著放大质保期承诺对中标结果的影响，使其他与履约同样重要的技术和服务因素被弱化。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议显著压降质保期延长的分值，改为围绕基础质保满足、备件保障、维修响应和维保组织等因素综合评价。",
            needs_human_review=False,
            human_review_reason=None,
            finding_origin="analyzer",
        )
    )
    return findings


def _add_software_copyright_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("软件著作权评分过高且与履约能力评价边界不清" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "软件著作权",
                "著作权登记证书",
                "资产管理读写基站",
                "城市大数据服务运营类",
                "城市公共信息服务云类",
                "物业垃圾分类自动化分捡类系统",
                "物业能源管理类软件",
                "物业电梯安全远程监控类系统",
                "物业消防设备监测自动化类系统",
                "物业空调运行自动化监测类系统",
            )
        )
        and any(marker in clause.text for marker in ("20分", "100 分", "最高得 100 分", "最高得100分"))
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="软件著作权评分过高且与履约能力评价边界不清",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分项以多类软件著作权或知识产权储备直接给出高分，且总分值较高。"
                "这类设计容易把知识产权占有状况直接转化为竞争优势，而弱化对实际平台运营、实施组织和服务质量的评价。"
            ),
            impact_on_competition_or_performance="可能放大既有知识产权储备优势，压缩具备履约能力但无对应著作权储备供应商的竞争空间。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
            rewrite_suggestion="建议删除高分值软件著作权堆叠评分，改为围绕实际应用场景、服务方案、运维组织和交付成果设置可核验的履约评价因素。",
            needs_human_review=True,
            human_review_reason="需结合采购范围、现有系统基础和实际服务需求判断软件著作权是否仅能作为辅助证明，还是已被不当放大为高分因素。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_experience_evaluation_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("经验评价叠加主观履约评价证明且分值过高" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "履约评价为满意",
                "履约评价为优秀",
                "其他同等评价",
                "国家机关或事业单位委托",
                "考核评价为",
                "总体履约评价结果",
                "优”或“优秀",
                "优或优秀",
                "医院物业",
                "三甲医院",
                "评审创建",
                "复审经验",
            )
        )
        and any(marker in clause.text for marker in ("10 分", "100分", "最高得 100 分", "最高得100分"))
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_scoring_weight",
            problem_title="经验评价叠加主观履约评价证明且分值过高",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "经验评分不仅要求同类项目，还要求合同相对方出具满意、优秀或同等履约评价，并设置较高总分值。"
                "这会把既有合作资源和主观评价证明一起转化为决定性竞争优势。"
            ),
            impact_on_competition_or_performance="可能显著抬高新进入供应商的竞争门槛，使既有合作沉淀和评价证明被过度放大。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；同类项目业绩案例解析（中国政府采购网）",
            rewrite_suggestion="建议压降经验评价总分值，删除满意或优秀等主观履约评价前提，改以项目规模、服务内容匹配度和履约完成证明作为辅助评价依据。",
            needs_human_review=True,
            human_review_reason="需结合项目特点和类似项目经验必要性判断相关经验与履约评价证明是否被不当放大为决定性高分条件。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_property_service_experience_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
    document_domain: DomainResolver,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if not _matches_catalog_domain(document, document_domain, catalog_classification, "property_service"):
        return findings
    if any("医院物业经验和医院评审经验评分高权重且叠加履约评价证明" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(marker in clause.text for marker in ("医院物业", "三甲医院", "评审创建", "复审经验", "履约评价为满意", "履约评价为优秀", "总体履约评价结果"))
        and any(marker in clause.text for marker in ("10 分", "20分", "40分", "60分", "100分", "最高得 100 分", "最高得100分"))
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="excessive_scoring_weight",
            problem_title="医院物业经验和医院评审经验评分高权重且叠加履约评价证明",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "评分项对医院物业经验、三甲医院评审创建或复审经验以及满意、优秀等履约评价证明给予较高分值。"
                "这会把既有医院项目沉淀和主观评价证明一起放大为高分优势，明显偏向少数既有供应商。"
            ),
            impact_on_competition_or_performance="可能抬高新进入供应商的竞争门槛，使既有医院项目履约证明被过度放大。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；同类项目业绩案例解析（中国政府采购网）",
            rewrite_suggestion="建议压降医院物业经验及医院评审经验权重，删除满意或优秀等主观履约评价前提，改以服务内容匹配度、项目规模和履约完成证明作为辅助评价因素。",
            needs_human_review=True,
            human_review_reason="需结合医院物业项目特点和类似项目经验必要性判断医院物业经验及医院评审经验是否被不当放大为决定性高分因素。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_brand_and_certification_scoring_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
    document_domain: DomainResolver,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    findings = _add_brand_scoring_theme_finding(
        document, findings, build_theme_finding=build_theme_finding, is_scoring_clause=is_scoring_clause
    )
    findings = _add_certification_scoring_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_scoring_clause=is_scoring_clause,
        document_domain=document_domain,
        catalog_classification=catalog_classification,
    )
    return findings


def _add_brand_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
) -> list[Finding]:
    if any("评分项直接按品牌档次赋分" in finding.problem_title for finding in findings):
        return findings
    if not _has_explicit_brand_scoring_clause(document, is_scoring_clause=is_scoring_clause):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and _contains_explicit_brand_marker(clause.text)
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
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


def _has_explicit_brand_scoring_clause(
    document: NormalizedDocument,
    *,
    is_scoring_clause: ClausePredicate,
) -> bool:
    return any(is_scoring_clause(clause) and _contains_explicit_brand_marker(clause.text) for clause in document.clauses)


def _contains_explicit_brand_marker(text: str) -> bool:
    if any(marker in text for marker in ("一线品牌", "国际知名品牌", "其他国产品牌")):
        return True
    patterns = (
        r"(品牌|厂商|制造商).{0,6}(格力|美的|海尔|大金|日立)",
        r"(格力|美的|海尔|大金|日立)(品牌|厂商|制造商|产品|设备|系列|得分|得\\d+分)",
        r"(?<![\\u4e00-\\u9fff])(格力|海尔|大金|日立)[、，,/\\s]",
        r"(?<![\\u4e00-\\u9fff])美的[、，,/\\s）)]",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _add_certification_scoring_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_scoring_clause: ClausePredicate,
    document_domain: DomainResolver,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any(
        finding.problem_title in {"认证评分混入错位证书且高分值结构失衡", "认证评分项目过密且高分值集中"}
        for finding in findings
    ):
        return findings
    explicit_cert_markers = (
        "认证证书",
        "体系认证",
        "商品售后服务评价",
        "售后服务认证",
        "五星售后",
        "品牌价值",
        "环境标志产品",
        "节能产品",
    )
    clauses = [
        clause
        for clause in document.clauses
        if is_scoring_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "高空清洗",
                "CCRC",
                "ISO20000",
                "认证证书",
                "生活垃圾分类",
                "商品售后服务评价",
                "售后服务认证",
                "五星售后",
                "品牌价值",
            )
        )
    ]
    if len(clauses) < 2 or not any(any(marker in clause.text for marker in explicit_cert_markers) for clause in clauses):
        return findings
    mismatch_markers = (
        "高空清洗",
        "CCRC",
        "ISO20000",
        "生活垃圾分类",
        "商品售后服务评价",
        "售后服务认证",
        "五星售后",
        "品牌价值",
        "有机产品认证",
        "先进单位",
        "注册安全工程师",
    )
    has_domain_mismatch = any(any(marker in clause.text for marker in mismatch_markers) for clause in clauses)
    if not has_domain_mismatch and _matches_catalog_domain(
        document,
        document_domain,
        catalog_classification,
        "furniture_goods",
    ):
        findings.append(
            build_theme_finding(
                document=document,
                clauses=clauses,
                issue_type="excessive_scoring_weight",
                problem_title="认证评分项目过密且高分值集中",
                risk_level="high",
                severity_score=3,
                confidence="high",
                compliance_judgment="likely_non_compliant",
                why_it_is_risky=(
                    "评分表连续设置体系认证、低VOCs、家具有害物质限量、抗菌和防霉等多类认证，并通过较高分值集中放大认证储备优势。"
                    "即使这些认证与家具场景存在一定关联，过密设置并叠加高分值，仍会使认证储备对中标结果产生过强影响。"
                ),
                impact_on_competition_or_performance="可能使认证储备而非供货质量、安装组织和售后履约能力成为主要得分来源，压缩其他具备履约能力供应商的竞争空间。",
                legal_or_policy_basis="政府采购需求管理办法（财政部）；综合评分法边界分析（中国政府采购网）",
                rewrite_suggestion="建议压降认证类总分值，避免连续设置多项高分认证；仅保留与家具质量控制和环保安全直接相关的少量辅助性证明，并取消中标后补证安排。",
                needs_human_review=True,
                human_review_reason="需结合医院家具场景的质量、环保和院感要求判断相关认证是否应保留，以及分值是否被不当放大。",
                finding_origin="analyzer",
            )
        )
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="scoring_content_mismatch",
            problem_title="认证评分混入错位证书且高分值结构失衡",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "认证评分中同时混入企业称号、跨领域证书和与项目主题关联不足的认证项，并通过较高分值结构集中放大。"
                "这类内容与项目供货和售后履约关联较弱，却被整体转化为高分竞争优势。"
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


def _matches_catalog_domain(
    document: NormalizedDocument,
    document_domain: DomainResolver,
    catalog_classification: CatalogClassification | None,
    domain_key: str,
) -> bool:
    return classification_has_domain(catalog_classification, domain_key) or document_domain(document) == domain_key


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
