from __future__ import annotations

from dataclasses import dataclass

from agent_compliance.core.schemas import Clause, Finding, NormalizedDocument


SCOPE_REQUIREMENT_BODY = "requirement_body"
SCOPE_SCORING_RULE = "scoring_rule"
SCOPE_TECHNICAL_REQUIREMENT = "technical_requirement"
SCOPE_COMMERCIAL_REQUIREMENT = "commercial_requirement"
SCOPE_ACCEPTANCE_REQUIREMENT = "acceptance_requirement"
SCOPE_TEMPLATE_TEXT = "template_text"
SCOPE_PROMPT_TEXT = "prompt_text"
SCOPE_FORMAT_TEXT = "format_text"
SCOPE_BACKGROUND_TEXT = "background_text"
SCOPE_ATTACHMENT_SAMPLE = "attachment_sample"

FUNCTION_QUALIFICATION_GATE = "qualification_gate"
FUNCTION_SCORING_FACTOR = "scoring_factor"
FUNCTION_SCORING_EVIDENCE = "scoring_evidence"
FUNCTION_TECHNICAL_PARAMETER = "technical_parameter"
FUNCTION_PROOF_REQUIREMENT = "proof_requirement"
FUNCTION_IMPLEMENTATION_OBLIGATION = "implementation_obligation"
FUNCTION_INTEGRATION_OBLIGATION = "integration_obligation"
FUNCTION_COMMERCIAL_TERM = "commercial_term"
FUNCTION_ACCEPTANCE_PROCEDURE = "acceptance_procedure"
FUNCTION_REFERENCE_NOTE = "reference_note"
FUNCTION_TEMPLATE_RESIDUE_CANDIDATE = "template_residue_candidate"

EFFECT_STRONG_BINDING = "strong_binding"
EFFECT_WEAK_BINDING = "weak_binding"
EFFECT_REFERENCE_ONLY = "reference_only"


@dataclass(frozen=True)
class RequirementScopeClassification:
    scope_type: str
    clause_function: str
    effect_strength: str
    is_effective_requirement: bool
    is_high_weight_requirement: bool
    reason: str
    confidence: str = "medium"

    @property
    def category(self) -> str:
        mapping = {
            SCOPE_REQUIREMENT_BODY: "body",
            SCOPE_SCORING_RULE: "body",
            SCOPE_TECHNICAL_REQUIREMENT: "body",
            SCOPE_COMMERCIAL_REQUIREMENT: "body",
            SCOPE_ACCEPTANCE_REQUIREMENT: "body",
            SCOPE_TEMPLATE_TEXT: "template",
            SCOPE_PROMPT_TEXT: "hint",
            SCOPE_FORMAT_TEXT: "format",
            SCOPE_BACKGROUND_TEXT: "body",
            SCOPE_ATTACHMENT_SAMPLE: "template",
        }
        return mapping.get(self.scope_type, "body")


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
    "仅作提示",
)

ATTACHMENT_MARKERS = (
    "附件",
    "附表",
    "样表",
)

QUALIFICATION_MARKERS = (
    "资格要求",
    "申请人的资格要求",
    "供应商资格",
    "供应商应当具备",
)

SCORING_MARKERS = (
    "评分项",
    "评分因素",
    "评分标准",
    "评标信息",
    "综合评分",
    "得分",
)

TECHNICAL_MARKERS = (
    "技术要求",
    "技术参数",
    "技术指标",
    "功能要求",
    "用户需求书",
    "配置要求",
)

COMMERCIAL_MARKERS = (
    "商务要求",
    "付款方式",
    "违约责任",
    "交货期限",
    "售后服务",
    "驻场",
    "响应时间",
)

ACCEPTANCE_MARKERS = (
    "验收",
    "检测",
    "测试",
    "送检",
    "复检",
    "专家评审",
    "最终确认",
)

INTEGRATION_MARKERS = (
    "接口",
    "系统端口",
    "开放软件端口",
    "无缝对接",
    "医院信息系统",
    "HIS",
    "PACS",
    "LIS",
    "数据交换",
)

REFERENCE_MARKERS = (
    "说明：",
    "说明",
    "注：",
    "注:",
    "备注：",
    "备注:",
    "参考",
)

STRONG_BINDING_MARKERS = (
    "应",
    "须",
    "必须",
    "不得",
    "需提供",
    "应提供",
    "由供应商承担",
    "由中标人承担",
    "否则",
    "取消资格",
    "得",
)

WEAK_BINDING_MARKERS = (
    "建议",
    "可结合实际",
    "可根据",
    "优先",
    "参考",
    "原则上",
)


def annotate_document_requirement_scope(document: NormalizedDocument) -> NormalizedDocument:
    for clause in document.clauses:
        apply_clause_scope_annotation(clause)
    return document


def apply_clause_scope_annotation(clause: Clause) -> Clause:
    classification = classify_clause_scope(clause)
    clause.scope_type = classification.scope_type
    clause.clause_function = classification.clause_function
    clause.effect_strength = classification.effect_strength
    clause.is_effective_requirement = classification.is_effective_requirement
    clause.is_high_weight_requirement = classification.is_high_weight_requirement
    clause.scope_confidence = classification.confidence
    return clause


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
    content = text or ""

    if _contains_any(combined, HINT_MARKERS):
        return RequirementScopeClassification(
            scope_type=SCOPE_PROMPT_TEXT,
            clause_function=FUNCTION_REFERENCE_NOTE,
            effect_strength=EFFECT_REFERENCE_ONLY,
            is_effective_requirement=False,
            is_high_weight_requirement=False,
            reason="命中提示性或平台操作性文本标记",
            confidence="high",
        )
    if _contains_any(combined, FORMAT_MARKERS):
        return RequirementScopeClassification(
            scope_type=SCOPE_FORMAT_TEXT,
            clause_function=FUNCTION_REFERENCE_NOTE,
            effect_strength=EFFECT_REFERENCE_ONLY,
            is_effective_requirement=False,
            is_high_weight_requirement=False,
            reason="命中投标文件格式或编制说明标记",
            confidence="high",
        )
    if _contains_any(combined, TEMPLATE_MARKERS):
        return RequirementScopeClassification(
            scope_type=SCOPE_TEMPLATE_TEXT,
            clause_function=FUNCTION_TEMPLATE_RESIDUE_CANDIDATE,
            effect_strength=EFFECT_REFERENCE_ONLY,
            is_effective_requirement=False,
            is_high_weight_requirement=False,
            reason="命中声明函、承诺函或授权模板标记",
            confidence="high",
        )
    if _contains_any(combined, ATTACHMENT_MARKERS) and _contains_any(combined, TEMPLATE_MARKERS):
        return RequirementScopeClassification(
            scope_type=SCOPE_ATTACHMENT_SAMPLE,
            clause_function=FUNCTION_TEMPLATE_RESIDUE_CANDIDATE,
            effect_strength=EFFECT_REFERENCE_ONLY,
            is_effective_requirement=False,
            is_high_weight_requirement=False,
            reason="命中附件样表和模板文本标记",
            confidence="medium",
        )

    scope_type = _infer_scope_type(combined, content)
    clause_function = _infer_clause_function(scope_type, combined, content)
    effect_strength = _infer_effect_strength(scope_type, clause_function, content)
    is_effective = scope_type not in {
        SCOPE_TEMPLATE_TEXT,
        SCOPE_PROMPT_TEXT,
        SCOPE_FORMAT_TEXT,
        SCOPE_ATTACHMENT_SAMPLE,
    }
    is_high_weight = is_effective and effect_strength == EFFECT_STRONG_BINDING and scope_type in {
        SCOPE_REQUIREMENT_BODY,
        SCOPE_SCORING_RULE,
        SCOPE_TECHNICAL_REQUIREMENT,
        SCOPE_COMMERCIAL_REQUIREMENT,
        SCOPE_ACCEPTANCE_REQUIREMENT,
    }
    reason = f"识别为{scope_type}，条款功能为{clause_function}，效力强度为{effect_strength}"
    return RequirementScopeClassification(
        scope_type=scope_type,
        clause_function=clause_function,
        effect_strength=effect_strength,
        is_effective_requirement=is_effective,
        is_high_weight_requirement=is_high_weight,
        reason=reason,
        confidence="medium",
    )


def classify_clause_scope(clause: Clause) -> RequirementScopeClassification:
    if clause.scope_type and clause.clause_function and clause.effect_strength:
        return RequirementScopeClassification(
            scope_type=clause.scope_type,
            clause_function=clause.clause_function,
            effect_strength=clause.effect_strength,
            is_effective_requirement=bool(clause.is_effective_requirement),
            is_high_weight_requirement=bool(clause.is_high_weight_requirement),
            reason="复用已标注的条款语义分层结果",
            confidence=clause.scope_confidence or "medium",
        )
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
    return classify_clause_scope(clause).is_effective_requirement


def is_high_weight_requirement_clause(clause: Clause) -> bool:
    return classify_clause_scope(clause).is_high_weight_requirement


def is_effective_requirement_finding(finding: Finding) -> bool:
    return classify_finding_scope(finding).is_effective_requirement


def is_high_weight_requirement_finding(finding: Finding) -> bool:
    return classify_finding_scope(finding).is_high_weight_requirement


def is_substantive_requirement_clause(clause: Clause) -> bool:
    classification = classify_clause_scope(clause)
    return classification.is_effective_requirement and classification.effect_strength != EFFECT_REFERENCE_ONLY


def is_substantive_requirement_finding(finding: Finding) -> bool:
    classification = classify_finding_scope(finding)
    return classification.is_effective_requirement and classification.effect_strength != EFFECT_REFERENCE_ONLY


def filter_effective_requirement_clauses(clauses: list[Clause]) -> list[Clause]:
    return [clause for clause in clauses if is_effective_requirement_clause(clause)]


def filter_high_weight_requirement_clauses(clauses: list[Clause]) -> list[Clause]:
    return [clause for clause in clauses if is_high_weight_requirement_clause(clause)]


def filter_substantive_requirement_clauses(clauses: list[Clause]) -> list[Clause]:
    return [clause for clause in clauses if is_substantive_requirement_clause(clause)]


def filter_effective_requirement_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if is_effective_requirement_finding(finding)]


def filter_substantive_requirement_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if is_substantive_requirement_finding(finding)]


def _infer_scope_type(combined: str, content: str) -> str:
    if _contains_any(content, REFERENCE_MARKERS) and not _contains_any(combined, SCORING_MARKERS):
        return SCOPE_BACKGROUND_TEXT
    if _contains_any(combined, SCORING_MARKERS):
        return SCOPE_SCORING_RULE
    if _contains_any(combined, QUALIFICATION_MARKERS):
        return SCOPE_REQUIREMENT_BODY
    if _contains_any(combined, ACCEPTANCE_MARKERS):
        return SCOPE_ACCEPTANCE_REQUIREMENT
    if _contains_any(combined, COMMERCIAL_MARKERS):
        return SCOPE_COMMERCIAL_REQUIREMENT
    if _contains_any(combined, TECHNICAL_MARKERS):
        return SCOPE_TECHNICAL_REQUIREMENT
    if _contains_any(content, REFERENCE_MARKERS):
        return SCOPE_BACKGROUND_TEXT
    return SCOPE_REQUIREMENT_BODY


def _infer_clause_function(scope_type: str, combined: str, content: str) -> str:
    if scope_type in {SCOPE_TEMPLATE_TEXT, SCOPE_ATTACHMENT_SAMPLE}:
        return FUNCTION_TEMPLATE_RESIDUE_CANDIDATE
    if scope_type in {SCOPE_PROMPT_TEXT, SCOPE_FORMAT_TEXT, SCOPE_BACKGROUND_TEXT}:
        return FUNCTION_REFERENCE_NOTE
    if _contains_any(combined, INTEGRATION_MARKERS) or _contains_any(content, INTEGRATION_MARKERS):
        return FUNCTION_INTEGRATION_OBLIGATION
    if scope_type == SCOPE_ACCEPTANCE_REQUIREMENT:
        return FUNCTION_ACCEPTANCE_PROCEDURE
    if scope_type == SCOPE_COMMERCIAL_REQUIREMENT:
        return FUNCTION_COMMERCIAL_TERM
    if scope_type == SCOPE_TECHNICAL_REQUIREMENT:
        if _contains_any(content, ("检测报告", "CMA", "CNAS", "证明材料", "报告")):
            return FUNCTION_PROOF_REQUIREMENT
        return FUNCTION_TECHNICAL_PARAMETER
    if scope_type == SCOPE_SCORING_RULE:
        if _contains_any(content, ("提供", "证明", "证书", "报告", "发票", "合同")):
            return FUNCTION_SCORING_EVIDENCE
        return FUNCTION_SCORING_FACTOR
    if _contains_any(combined, QUALIFICATION_MARKERS) or _contains_any(content, ("资格", "资质", "年限", "业绩")):
        return FUNCTION_QUALIFICATION_GATE
    if _contains_any(content, ("安装", "调试", "驻场", "配合", "交付")):
        return FUNCTION_IMPLEMENTATION_OBLIGATION
    return FUNCTION_REFERENCE_NOTE


def _infer_effect_strength(scope_type: str, clause_function: str, content: str) -> str:
    if scope_type in {
        SCOPE_TEMPLATE_TEXT,
        SCOPE_PROMPT_TEXT,
        SCOPE_FORMAT_TEXT,
        SCOPE_ATTACHMENT_SAMPLE,
        SCOPE_BACKGROUND_TEXT,
    }:
        return EFFECT_REFERENCE_ONLY
    if _contains_any(content, WEAK_BINDING_MARKERS):
        return EFFECT_WEAK_BINDING
    if _contains_any(content, REFERENCE_MARKERS) and clause_function == FUNCTION_REFERENCE_NOTE:
        return EFFECT_REFERENCE_ONLY
    if _contains_any(content, STRONG_BINDING_MARKERS):
        return EFFECT_STRONG_BINDING
    return EFFECT_WEAK_BINDING


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
