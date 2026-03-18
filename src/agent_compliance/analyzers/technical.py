from __future__ import annotations

from typing import Any, Callable

from agent_compliance.schemas import Finding, NormalizedDocument


ClausePredicate = Callable[[Any], bool]
ThemeBuilder = Callable[..., Finding]


def apply_technical_analyzers(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_technical_clause: ClausePredicate,
) -> list[Finding]:
    findings = _add_technical_standard_mismatch_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_technical_clause=is_technical_clause,
    )
    findings = _add_proof_formality_findings(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_technical_clause=is_technical_clause,
    )
    return findings


def _add_technical_standard_mismatch_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_technical_clause: ClausePredicate,
) -> list[Finding]:
    if any("技术要求引用了与标的不匹配的标准或规范" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_technical_clause(clause)
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
                "GB/T 26701",
                "DB44/T",
                "EN14175-3",
                "ISO 20743",
                "ISO20743",
                "ISO 10993",
                "ISO10993",
                "地方标准",
                "保洁服务",
                "桥梁荷载试验",
                "菜肴罐头",
                "食品加工",
                "系统平台",
                "软件接口",
                "高空清洗",
                "水运工程",
            )
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="technical_reference_mismatch",
            problem_title="技术要求引用了与标的不匹配的标准或规范",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
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


def _add_proof_formality_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_technical_clause: ClausePredicate,
) -> list[Finding]:
    if any("技术证明材料形式要求过严且带有地方化限制" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_technical_clause(clause)
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
                "全国认证认可信息公共服务平台",
                "CMA  资质许可（认定）范围内",
                "CMA资质许可（认定）范围内",
                "经广告审查机关备案的产品彩页",
                "专项检测报告",
            )
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
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
