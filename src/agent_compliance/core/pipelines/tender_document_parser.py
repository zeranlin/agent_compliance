from __future__ import annotations

from collections import OrderedDict

from agent_compliance.core.pipelines.requirement_scope_layer import annotate_document_requirement_scope
from agent_compliance.core.pipelines.tender_document_risk_scope_layer import (
    RISK_SCOPE_CORE,
    RISK_SCOPE_OUT,
    RISK_SCOPE_SUPPORTING,
    annotate_tender_document_risk_scope,
)
from agent_compliance.core.schemas import Clause, NormalizedDocument, StructuredTenderDocument, StructuredTenderSection

TENDER_PARSER_MODE_OFF = "off"
TENDER_PARSER_MODE_ASSIST = "assist"
TENDER_PARSER_MODE_REQUIRED = "required"
VALID_TENDER_PARSER_MODES = {
    TENDER_PARSER_MODE_OFF,
    TENDER_PARSER_MODE_ASSIST,
    TENDER_PARSER_MODE_REQUIRED,
}


def resolve_tender_parser_mode(mode: str | None) -> str:
    value = (mode or TENDER_PARSER_MODE_OFF).strip().lower()
    if value not in VALID_TENDER_PARSER_MODES:
        return TENDER_PARSER_MODE_OFF
    return value


def prepare_review_document(
    document: NormalizedDocument,
    *,
    parser_mode: str | None = None,
) -> tuple[NormalizedDocument, StructuredTenderDocument | None]:
    resolved_mode = resolve_tender_parser_mode(parser_mode)
    annotate_tender_document_risk_scope(document)
    annotate_document_requirement_scope(document)
    if resolved_mode == TENDER_PARSER_MODE_OFF:
        return document, None
    structured = parse_tender_document(document, parser_mode=resolved_mode)
    if resolved_mode == TENDER_PARSER_MODE_REQUIRED and structured.core_section_count == 0:
        raise ValueError("招标文件独立解析未识别出核心风险板块，无法以 required 模式进入审查主链")
    return document, structured


def parse_tender_document(
    document: NormalizedDocument,
    *,
    parser_mode: str = TENDER_PARSER_MODE_ASSIST,
) -> StructuredTenderDocument:
    annotate_tender_document_risk_scope(document)
    annotate_document_requirement_scope(document)
    grouped: "OrderedDict[tuple[str, str, str], list]" = OrderedDict()
    for clause in document.clauses:
        key = (
            clause.document_structure_type or "unknown",
            clause.risk_scope or RISK_SCOPE_OUT,
            clause.source_section or clause.section_path or clause.document_structure_type or "未识别板块",
        )
        grouped.setdefault(key, []).append(clause)

    sections: list[StructuredTenderSection] = []
    for index, ((document_structure_type, risk_scope, title), clauses) in enumerate(grouped.items(), start=1):
        scope_reasons = _unique_preserve_order(
            clause.scope_reason for clause in clauses if clause.scope_reason
        )
        sections.append(
            StructuredTenderSection(
                section_id=f"S-{index:03d}",
                document_structure_type=document_structure_type,
                risk_scope=risk_scope,
                title=title,
                clause_ids=[clause.clause_id for clause in clauses],
                clause_count=len(clauses),
                effective_clause_count=sum(1 for clause in clauses if clause.is_effective_requirement),
                high_weight_clause_count=sum(1 for clause in clauses if clause.is_high_weight_requirement),
                scope_reasons=scope_reasons,
            )
        )

    return StructuredTenderDocument(
        source_path=document.source_path,
        document_name=document.document_name,
        parser_mode=resolve_tender_parser_mode(parser_mode),
        section_count=len(sections),
        sections=sections,
        core_section_count=sum(1 for section in sections if section.risk_scope == RISK_SCOPE_CORE),
        supporting_section_count=sum(1 for section in sections if section.risk_scope == RISK_SCOPE_SUPPORTING),
        out_of_scope_section_count=sum(1 for section in sections if section.risk_scope == RISK_SCOPE_OUT),
    )


def _unique_preserve_order(values) -> list[str]:
    ordered: OrderedDict[str, None] = OrderedDict()
    for value in values:
        ordered[str(value)] = None
    return list(ordered.keys())


def collect_structured_clause_ids(
    structured_document: StructuredTenderDocument | None,
    *,
    structure_types: tuple[str, ...] | None = None,
    risk_scopes: tuple[str, ...] | None = None,
) -> set[str]:
    if structured_document is None:
        return set()
    clause_ids: set[str] = set()
    for section in structured_document.sections:
        if structure_types and section.document_structure_type not in structure_types:
            continue
        if risk_scopes and section.risk_scope not in risk_scopes:
            continue
        clause_ids.update(section.clause_ids)
    return clause_ids


def clause_in_structured_sections(
    clause: Clause,
    structured_document: StructuredTenderDocument | None,
    *,
    structure_types: tuple[str, ...] | None = None,
    risk_scopes: tuple[str, ...] | None = None,
) -> bool:
    if structured_document is None:
        return False
    return clause.clause_id in collect_structured_clause_ids(
        structured_document,
        structure_types=structure_types,
        risk_scopes=risk_scopes,
    )
