from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from agent_compliance.core.knowledge.issue_type_authority_map import (
    IssueTypeAuthorityRecord,
    get_issue_type_authority_record,
)
from agent_compliance.core.knowledge.legal_clause_index import (
    LegalClauseRecord,
    load_legal_clause_records,
)
from agent_compliance.core.schemas import Finding


@dataclass(frozen=True)
class LegalAuthorityReasoning:
    primary_authority: str | None
    secondary_authorities: tuple[str, ...]
    legal_or_policy_basis: str | None
    authority_key_points: str | None
    applicability_logic: str | None
    needs_human_review: bool
    human_review_reason: str | None


def apply_legal_authority_reasoner(findings: list[Finding]) -> list[Finding]:
    for finding in findings:
        reasoning = reason_for_finding(finding)
        if reasoning is None:
            continue
        finding.primary_authority = reasoning.primary_authority
        finding.secondary_authorities = list(reasoning.secondary_authorities)
        finding.legal_or_policy_basis = reasoning.legal_or_policy_basis
        finding.authority_key_points = reasoning.authority_key_points
        finding.applicability_logic = reasoning.applicability_logic
        finding.needs_human_review = reasoning.needs_human_review
        finding.human_review_reason = reasoning.human_review_reason
    return findings


def reason_for_finding(finding: Finding) -> LegalAuthorityReasoning | None:
    record = get_issue_type_authority_record(finding.issue_type)
    if record is None:
        return None

    primary_groups = _resolve_authority_groups(record.primary_clause_ids, record.primary_reference_ids)
    secondary_groups = _resolve_authority_groups(record.secondary_clause_ids, record.secondary_reference_ids)
    authority_key_points = _build_authority_key_points(record.primary_clause_ids, record.secondary_clause_ids)

    primary_authority = primary_groups[0] if primary_groups else None
    secondary_authorities = tuple(group for group in secondary_groups if group != primary_authority)
    legal_or_policy_basis = _merge_legal_basis(
        finding.legal_or_policy_basis,
        primary_authority=primary_authority,
        secondary_authorities=secondary_authorities,
    )
    applicability_logic = _build_applicability_logic(record, finding)
    needs_human_review, human_review_reason = _resolve_human_review(record, finding)

    return LegalAuthorityReasoning(
        primary_authority=primary_authority,
        secondary_authorities=secondary_authorities,
        legal_or_policy_basis=legal_or_policy_basis,
        authority_key_points=authority_key_points,
        applicability_logic=applicability_logic,
        needs_human_review=needs_human_review,
        human_review_reason=human_review_reason,
    )


def _build_applicability_logic(record: IssueTypeAuthorityRecord, finding: Finding) -> str:
    parts = [record.reasoning_template]
    section_context = finding.section_path or finding.source_section or ""
    if section_context:
        parts.append(f"当前条款位于“{section_context}”相关上下文，应结合该章节在采购流程中的功能判断上述依据是否直接适用。")
    return " ".join(parts)


def _resolve_human_review(
    record: IssueTypeAuthorityRecord,
    finding: Finding,
) -> tuple[bool, str | None]:
    needs_human_review = finding.needs_human_review or finding.issue_type in {
        "technical_justification_needed",
        "qualification_domain_mismatch",
        "scoring_content_mismatch",
        "unclear_acceptance_standard",
    }
    legal_review_reason = _build_legal_review_reason(record)
    if not needs_human_review:
        return False, finding.human_review_reason
    return True, _merge_human_review_reason(finding.human_review_reason, legal_review_reason)


def _build_legal_review_reason(record: IssueTypeAuthorityRecord) -> str | None:
    reasons = [item for item in record.requires_human_review_when if item]
    if not reasons:
        return None
    return "法规侧复核重点：" + "；".join(reasons[:2])


def _merge_human_review_reason(existing: str | None, generated: str | None) -> str | None:
    parts: list[str] = []
    for item in (existing, generated):
        text = (item or "").strip()
        if text and text not in parts:
            parts.append(text)
    if not parts:
        return None
    return " ".join(parts)


def _merge_legal_basis(
    existing: str | None,
    *,
    primary_authority: str | None,
    secondary_authorities: tuple[str, ...],
) -> str | None:
    parts: list[str] = []
    existing = (existing or "").strip()
    if existing:
        parts.append(existing)
    if primary_authority:
        parts.append(f"主依据：{primary_authority}")
    if secondary_authorities:
        parts.append(f"辅依据：{'；'.join(secondary_authorities[:3])}")
    deduped: list[str] = []
    for item in parts:
        if item not in deduped:
            deduped.append(item)
    return "；".join(deduped) if deduped else None


def _resolve_authority_groups(clause_ids: tuple[str, ...], reference_ids: tuple[str, ...]) -> tuple[str, ...]:
    groups: list[str] = []
    clause_records = [_clause_record_map().get(item) for item in clause_ids]
    clause_records = [item for item in clause_records if item is not None]
    for reference_id in reference_ids:
        related = [item for item in clause_records if item.reference_id == reference_id]
        if related:
            groups.append(_format_clause_group(related))
            continue
        fallback = _first_clause_for_reference(reference_id)
        if fallback is not None:
            groups.append(f"《{fallback.doc_title}》")
    for record in clause_records:
        formatted = _format_clause_group([record])
        if formatted not in groups:
            groups.append(formatted)
    return tuple(groups)


def _build_authority_key_points(
    primary_clause_ids: tuple[str, ...],
    secondary_clause_ids: tuple[str, ...],
) -> str | None:
    seen: set[str] = set()
    parts: list[str] = []
    for clause_id in (*primary_clause_ids, *secondary_clause_ids):
        record = _clause_record_map().get(clause_id)
        if record is None:
            continue
        key = record.clause_id
        if key in seen:
            continue
        seen.add(key)
        label = record.article_label or record.chapter_label or "相关条款"
        summary = _summarize_clause_text(record.clause_text)
        parts.append(f"{label}：{summary}")
        if len(parts) >= 4:
            break
    if not parts:
        return None
    return "；".join(parts)


def _summarize_clause_text(text: str, *, limit: int = 44) -> str:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        return "暂无条文要点"
    for separator in ("。", "；", ";"):
        if separator in normalized:
            first = normalized.split(separator, 1)[0].strip()
            if first:
                normalized = first
                break
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def _format_clause_group(records: list[LegalClauseRecord]) -> str:
    ordered = sorted(records, key=lambda item: item.clause_id)
    doc_title = ordered[0].doc_title
    labels = [item.article_label for item in ordered if item.article_label]
    if labels:
        return f"《{doc_title}》{'、'.join(labels)}"
    return f"《{doc_title}》"


@lru_cache(maxsize=1)
def _clause_record_map() -> dict[str, LegalClauseRecord]:
    return {record.clause_id: record for record in load_legal_clause_records()}


@lru_cache(maxsize=1)
def _reference_first_clause_map() -> dict[str, LegalClauseRecord]:
    mapping: dict[str, LegalClauseRecord] = {}
    for record in load_legal_clause_records():
        mapping.setdefault(record.reference_id, record)
    return mapping


def _first_clause_for_reference(reference_id: str) -> LegalClauseRecord | None:
    return _reference_first_clause_map().get(reference_id)
