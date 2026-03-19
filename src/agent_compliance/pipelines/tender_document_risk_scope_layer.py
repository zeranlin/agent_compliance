from __future__ import annotations

from dataclasses import dataclass

from agent_compliance.schemas import Clause, NormalizedDocument


STRUCTURE_NOTICE_INFO = "notice_info"
STRUCTURE_BIDDER_INSTRUCTIONS = "bidder_instructions"
STRUCTURE_QUALIFICATION_REVIEW = "qualification_review"
STRUCTURE_CONFORMITY_REVIEW = "conformity_review"
STRUCTURE_SCORING_RULES = "scoring_rules"
STRUCTURE_TECHNICAL_REQUIREMENTS = "technical_requirements"
STRUCTURE_COMMERCIAL_REQUIREMENTS = "commercial_requirements"
STRUCTURE_ACCEPTANCE_REQUIREMENTS = "acceptance_requirements"
STRUCTURE_CONTRACT_TERMS = "contract_terms"
STRUCTURE_ATTACHMENTS_TEMPLATES = "attachments_templates"

RISK_SCOPE_CORE = "core_risk_scope"
RISK_SCOPE_SUPPORTING = "supporting_risk_scope"
RISK_SCOPE_OUT = "out_of_scope"


@dataclass(frozen=True)
class TenderDocumentRiskScopeClassification:
    document_structure_type: str
    risk_scope: str
    scope_reason: str
    confidence: str = "medium"


NOTICE_MARKERS = ("招标公告", "项目概况", "获取招标文件", "提交投标文件截止时间", "开标时间", "采购人信息")
BIDDER_INSTRUCTION_MARKERS = ("投标人须知", "投标文件组成要求及格式", "编制要求", "投标须知", "投标人须知前附表")
QUALIFICATION_MARKERS = ("资格性审查", "资格要求", "申请人的资格要求", "供应商资格", "资格审查表")
CONFORMITY_MARKERS = ("符合性审查", "符合性审查表", "实质性响应", "符合性检查")
SCORING_MARKERS = ("评标信息", "评分项", "评分因素", "评分标准", "综合评分", "评审项")
TECHNICAL_MARKERS = ("用户需求书", "技术要求", "技术参数", "技术指标", "配置要求")
COMMERCIAL_MARKERS = ("商务要求", "售后服务", "交货期限", "付款方式", "违约责任", "履约担保")
ACCEPTANCE_MARKERS = ("验收", "送检", "复检", "检测", "测试", "专家评审", "最终确认")
CONTRACT_MARKERS = ("合同条款", "合同主要条款", "合同条款及格式", "解除合同", "赔偿", "违约责任")
ATTACHMENT_MARKERS = ("投标函", "承诺函", "声明函", "授权委托书", "法定代表人证明书", "附件", "样表")
ATTACHMENT_TEMPLATE_MARKERS = ("政府采购投标及履约承诺函", "中小企业声明函", "残疾人福利性单位声明函", "监狱企业声明函")


def annotate_tender_document_risk_scope(document: NormalizedDocument) -> NormalizedDocument:
    for clause in document.clauses:
        apply_tender_document_risk_scope_annotation(clause)
    return document


def apply_tender_document_risk_scope_annotation(clause: Clause) -> Clause:
    classification = classify_tender_document_risk_scope(clause)
    clause.document_structure_type = classification.document_structure_type
    clause.risk_scope = classification.risk_scope
    clause.scope_reason = classification.scope_reason
    return clause


def classify_tender_document_risk_scope(clause: Clause) -> TenderDocumentRiskScopeClassification:
    combined = " ".join(
        part
        for part in (
            clause.section_path or "",
            clause.source_section or "",
            clause.table_or_item_label or "",
            clause.text or "",
        )
        if part
    )
    structure = _infer_structure_type(combined)
    risk_scope = _infer_risk_scope(structure)
    reason = _scope_reason(structure, risk_scope)
    return TenderDocumentRiskScopeClassification(
        document_structure_type=structure,
        risk_scope=risk_scope,
        scope_reason=reason,
    )


def is_core_risk_scope_clause(clause: Clause) -> bool:
    if clause.risk_scope:
        return clause.risk_scope == RISK_SCOPE_CORE
    return classify_tender_document_risk_scope(clause).risk_scope == RISK_SCOPE_CORE


def is_supporting_or_core_risk_scope_clause(clause: Clause) -> bool:
    risk_scope = clause.risk_scope or classify_tender_document_risk_scope(clause).risk_scope
    return risk_scope in {RISK_SCOPE_CORE, RISK_SCOPE_SUPPORTING}


def _infer_structure_type(text: str) -> str:
    if _contains_any(text, ATTACHMENT_MARKERS):
        return STRUCTURE_ATTACHMENTS_TEMPLATES
    if _contains_any(text, ATTACHMENT_TEMPLATE_MARKERS):
        return STRUCTURE_ATTACHMENTS_TEMPLATES
    if _contains_any(text, QUALIFICATION_MARKERS):
        return STRUCTURE_QUALIFICATION_REVIEW
    if _contains_any(text, CONFORMITY_MARKERS):
        return STRUCTURE_CONFORMITY_REVIEW
    if _contains_any(text, SCORING_MARKERS):
        return STRUCTURE_SCORING_RULES
    if _contains_any(text, ACCEPTANCE_MARKERS):
        return STRUCTURE_ACCEPTANCE_REQUIREMENTS
    if _contains_any(text, COMMERCIAL_MARKERS):
        return STRUCTURE_COMMERCIAL_REQUIREMENTS
    if _contains_any(text, CONTRACT_MARKERS):
        return STRUCTURE_CONTRACT_TERMS
    if _contains_any(text, TECHNICAL_MARKERS):
        return STRUCTURE_TECHNICAL_REQUIREMENTS
    if _contains_any(text, BIDDER_INSTRUCTION_MARKERS):
        return STRUCTURE_BIDDER_INSTRUCTIONS
    if _contains_any(text, NOTICE_MARKERS):
        return STRUCTURE_NOTICE_INFO
    return STRUCTURE_TECHNICAL_REQUIREMENTS


def _infer_risk_scope(structure: str) -> str:
    if structure in {
        STRUCTURE_QUALIFICATION_REVIEW,
        STRUCTURE_SCORING_RULES,
        STRUCTURE_TECHNICAL_REQUIREMENTS,
        STRUCTURE_COMMERCIAL_REQUIREMENTS,
        STRUCTURE_ACCEPTANCE_REQUIREMENTS,
        STRUCTURE_CONTRACT_TERMS,
    }:
        return RISK_SCOPE_CORE
    if structure in {STRUCTURE_BIDDER_INSTRUCTIONS, STRUCTURE_CONFORMITY_REVIEW}:
        return RISK_SCOPE_SUPPORTING
    return RISK_SCOPE_OUT


def _scope_reason(structure: str, risk_scope: str) -> str:
    if risk_scope == RISK_SCOPE_CORE:
        return f"属于{structure}，直接承载采购需求风险判断"
    if risk_scope == RISK_SCOPE_SUPPORTING:
        return f"属于{structure}，可辅助判断但不应与核心采购需求正文同权"
    return f"属于{structure}，默认不作为采购需求风险主判断的高权重来源"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
