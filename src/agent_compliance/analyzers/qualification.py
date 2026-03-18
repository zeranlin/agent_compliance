from __future__ import annotations

from typing import Any, Callable

from agent_compliance.schemas import Finding, NormalizedDocument


ClausePredicate = Callable[[Any], bool]
ThemeBuilder = Callable[..., Finding]


def apply_qualification_analyzers(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_qualification_clause: ClausePredicate,
) -> list[Finding]:
    findings = _add_qualification_financial_scale_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_qualification_clause=is_qualification_clause,
    )
    findings = _add_qualification_operating_scope_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_qualification_clause=is_qualification_clause,
    )
    findings = _add_qualification_industry_appropriateness_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_qualification_clause=is_qualification_clause,
    )
    findings = _add_qualification_reasoning_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_qualification_clause=is_qualification_clause,
    )
    return findings


def looks_like_supplier_level_qualification_clause(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "投标人",
            "投标单位",
            "供应商",
            "企业",
            "公司",
            "经营场所",
            "营业收入",
            "资产总额",
            "参保人数",
            "纳税总额",
            "经营年限",
            "注册资本",
            "单项合同金额",
            "具备以下资质",
            "具有以下资质",
        )
    )


def _add_qualification_financial_scale_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_qualification_clause: ClausePredicate,
) -> list[Finding]:
    if any("资格条件设置一般财务和规模门槛" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_qualification_clause(clause)
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
                "净资产（所有者权益）必须不低于",
                "净资产不低于",
                "注册资本不低于",
                "年收入不低于",
                "净利润不低于",
            )
        )
    ]
    matched_marker_count = sum(
        1
        for marker in ("纳税", "员工总数", "参保人数", "资产总额", "净资产", "注册资本", "年收入", "净利润")
        if any(marker in clause.text for clause in clauses)
    )
    if not clauses or matched_marker_count < 2:
        return findings
    findings.append(
        build_theme_finding(
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
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_qualification_clause: ClausePredicate,
) -> list[Finding]:
    if any("资格条件设置经营年限、属地场所或单项业绩门槛" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_qualification_clause(clause)
        and any(
            marker in clause.text
            for marker in (
                "营业执照的成立日期不得晚于",
                "成立日期必须早于",
                "成立时间不少于",
                "营业执照注册地址必须位于",
                "固定的售后服务场所",
                "主要经营地址",
                "经营地址（非注册地址）",
                "主城四区范围内",
                "福州市",
                "单项合同金额不低于",
                "经营年限不低于",
                "外商投资及民营企业",
            )
        )
    ]
    if len(clauses) < 2:
        return findings
    findings.append(
        build_theme_finding(
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
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_qualification_clause: ClausePredicate,
) -> list[Finding]:
    if any("资格条件中存在与标的域不匹配的行业资质或专门许可" in finding.problem_title for finding in findings):
        return findings
    mismatch_markers = (
        "水运工程监理甲级",
        "有害生物防制",
        "SPCA",
        "学生饮用奶定点生产企业资格",
        "特种设备安全管理和作业人员证书",
        "棉花加工资格",
        "高空清洗悬吊作业企业安全生产证书",
        "高新技术企业证书",
        "企业诚信管理体系认证证书",
        "《企业诚信管理体系认证证书》",
    )
    clauses = [
        clause
        for clause in document.clauses
        if is_qualification_clause(clause)
        and looks_like_supplier_level_qualification_clause(clause.text or "")
        and any(marker in clause.text for marker in mismatch_markers)
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
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
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_qualification_clause: ClausePredicate,
) -> list[Finding]:
    if any("资格条件整体超出法定准入和履约必需范围" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_qualification_clause(clause)
        and looks_like_supplier_level_qualification_clause(clause.text or "")
        and any(
            marker in clause.text
            for marker in (
                "纳税总额",
                "年均纳税",
                "实际缴纳的增值税及企业所得税",
                "参保人数",
                "员工总数",
                "资产总额",
                "净资产",
                "成立日期",
                "成立时间",
                "固定的售后服务场所",
                "营业执照注册地址必须位于",
                "主要经营地址",
                "单项合同金额",
                "水运工程监理甲级",
                "有害生物防制",
                "SPCA",
                "学生饮用奶定点生产企业资格",
                "棉花加工资格",
                "特种设备安全管理和作业人员证书",
                "高空清洗悬吊作业企业安全生产证书",
                "高新技术企业证书",
                "国家级高新技术企业",
                "上级主管单位",
                "审计报告",
                "国家级特色企业",
                "企业诚信管理体系认证证书",
                "《企业诚信管理体系认证证书》",
                "农民专业合作社不具备投标资格",
                "外商投资及民营企业",
                "注册资本不低于",
                "年收入不低于",
                "净利润不低于",
                "股权结构",
                "经营年限不低于",
            )
        )
    ]
    if len(clauses) < 3:
        return findings
    findings.append(
        build_theme_finding(
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

