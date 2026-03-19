from __future__ import annotations

from dataclasses import dataclass

from agent_compliance.schemas import Clause, Finding


REQUIREMENT_SCOPE_BODY = "body"
REQUIREMENT_SCOPE_TEMPLATE = "template"
REQUIREMENT_SCOPE_HINT = "hint"
REQUIREMENT_SCOPE_FORMAT = "format"


@dataclass(frozen=True)
class RequirementScopeClassification:
    category: str
    reason: str


FORMAT_MARKERS = (
    "投标文件组成要求及格式",
    "编制指引",
    "填写说明",
    "格式自定",
    "投标文件组成：",
    "投标文件正文（信息公开部分）",
    "信息公开部分的内容到此为止",
    "投标文件附件（信息不公开部分）",
    "投标人情况及资格证明文件",
)

TEMPLATE_MARKERS = (
    "中小企业声明函",
    "残疾人福利性单位声明函",
    "监狱企业声明函",
    "政府采购投标及履约承诺函",
    "投标及履约承诺函",
    "投标函",
    "声明函",
    "承诺函",
    "授权委托书",
    "法定代表人证明书",
    "法定代表人资格证明书",
)

HINT_MARKERS = (
    "特别警示条款",
    "特别提示",
    "温馨提示",
    "风险知悉确认书",
    "政府采购违法行为风险知悉确认书",
    "投标文件制作工具",
    "投标书编制软件",
    "深圳政府采购智慧平台",
    "文件创建标识码",
    "文件制作机器码",
    "与其他投标供应商的投标文件由同一单位或者同一人编制",
    "如有方案表述中有出现类似可实现、实现、可支持、支持等描述",
    "仅作提示",
)

BODY_MARKERS = (
    "用户需求书",
    "技术要求",
    "商务要求",
    "评分项",
    "评分因素",
    "评标信息",
    "申请人的资格要求",
    "资格要求",
    "合同条款",
    "验收条件",
    "付款方式",
    "违约责任",
)


def classify_requirement_scope(
    *,
    clause_id: str | None = None,
    section_path: str | None = None,
    source_section: str | None = None,
    table_or_item_label: str | None = None,
    text: str | None = None,
) -> RequirementScopeClassification:
    combined = " ".join(
        part
        for part in (
            clause_id or "",
            section_path or "",
            source_section or "",
            table_or_item_label or "",
            text or "",
        )
        if part
    )

    if _contains_any(combined, HINT_MARKERS):
        return RequirementScopeClassification(
            category=REQUIREMENT_SCOPE_HINT,
            reason="命中提示性或平台操作性文本标记",
        )
    if _contains_any(combined, FORMAT_MARKERS):
        return RequirementScopeClassification(
            category=REQUIREMENT_SCOPE_FORMAT,
            reason="命中投标文件格式或编制说明标记",
        )
    if _contains_any(combined, TEMPLATE_MARKERS):
        return RequirementScopeClassification(
            category=REQUIREMENT_SCOPE_TEMPLATE,
            reason="命中声明函、承诺函或授权模板标记",
        )
    if _contains_any(combined, BODY_MARKERS):
        return RequirementScopeClassification(
            category=REQUIREMENT_SCOPE_BODY,
            reason="命中采购需求、评分、资格、技术或商务正文标记",
        )
    return RequirementScopeClassification(
        category=REQUIREMENT_SCOPE_BODY,
        reason="未命中模板、提示或格式标记，按正式正文处理",
    )


def classify_clause_scope(clause: Clause) -> RequirementScopeClassification:
    return classify_requirement_scope(
        clause_id=clause.clause_id,
        section_path=clause.section_path,
        source_section=clause.source_section,
        table_or_item_label=clause.table_or_item_label,
        text=clause.text,
    )


def classify_finding_scope(finding: Finding) -> RequirementScopeClassification:
    return classify_requirement_scope(
        clause_id=finding.clause_id,
        section_path=finding.section_path,
        source_section=finding.source_section,
        table_or_item_label=finding.table_or_item_label,
        text=finding.source_text,
    )


def is_effective_requirement_clause(clause: Clause) -> bool:
    return classify_clause_scope(clause).category == REQUIREMENT_SCOPE_BODY


def is_effective_requirement_finding(finding: Finding) -> bool:
    return classify_finding_scope(finding).category == REQUIREMENT_SCOPE_BODY


def filter_effective_requirement_clauses(clauses: list[Clause]) -> list[Clause]:
    return [clause for clause in clauses if is_effective_requirement_clause(clause)]


def filter_effective_requirement_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if is_effective_requirement_finding(finding)]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
