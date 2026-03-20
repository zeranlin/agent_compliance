from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Clause:
    clause_id: str
    text: str
    line_start: int
    line_end: int
    source_section: str | None = None
    section_path: str | None = None
    table_or_item_label: str | None = None
    page_hint: str | None = None
    document_structure_type: str | None = None
    risk_scope: str | None = None
    scope_reason: str | None = None
    scope_type: str | None = None
    clause_function: str | None = None
    effect_strength: str | None = None
    is_effective_requirement: bool | None = None
    is_high_weight_requirement: bool | None = None
    scope_confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Clause":
        return cls(**payload)


@dataclass
class PageSpan:
    page_number: int
    line_start: int
    line_end: int
    is_estimated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PageSpan":
        return cls(**payload)


@dataclass
class NormalizedDocument:
    source_path: str
    document_name: str
    file_hash: str
    normalized_text_path: str
    clause_count: int
    clauses: list[Clause]
    page_map: list[PageSpan] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "document_name": self.document_name,
            "file_hash": self.file_hash,
            "normalized_text_path": self.normalized_text_path,
            "clause_count": self.clause_count,
            "clauses": [clause.to_dict() for clause in self.clauses],
            "page_map": [page.to_dict() for page in self.page_map],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NormalizedDocument":
        return cls(
            source_path=payload["source_path"],
            document_name=payload["document_name"],
            file_hash=payload["file_hash"],
            normalized_text_path=payload["normalized_text_path"],
            clause_count=payload["clause_count"],
            clauses=[Clause.from_dict(item) for item in payload["clauses"]],
            page_map=[PageSpan.from_dict(item) for item in payload.get("page_map", [])],
            created_at=payload.get("created_at", utc_now_iso()),
        )


@dataclass
class StructuredTenderSection:
    section_id: str
    document_structure_type: str
    risk_scope: str
    title: str | None
    clause_ids: list[str]
    clause_count: int
    effective_clause_count: int
    high_weight_clause_count: int
    scope_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StructuredTenderSection":
        return cls(**payload)


@dataclass
class StructuredTenderDocument:
    source_path: str
    document_name: str
    parser_mode: str
    section_count: int
    sections: list[StructuredTenderSection]
    core_section_count: int
    supporting_section_count: int
    out_of_scope_section_count: int
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "document_name": self.document_name,
            "parser_mode": self.parser_mode,
            "section_count": self.section_count,
            "sections": [section.to_dict() for section in self.sections],
            "core_section_count": self.core_section_count,
            "supporting_section_count": self.supporting_section_count,
            "out_of_scope_section_count": self.out_of_scope_section_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StructuredTenderDocument":
        return cls(
            source_path=payload["source_path"],
            document_name=payload["document_name"],
            parser_mode=payload["parser_mode"],
            section_count=payload["section_count"],
            sections=[StructuredTenderSection.from_dict(item) for item in payload["sections"]],
            core_section_count=payload["core_section_count"],
            supporting_section_count=payload["supporting_section_count"],
            out_of_scope_section_count=payload["out_of_scope_section_count"],
            created_at=payload.get("created_at", utc_now_iso()),
        )


@dataclass
class RuleHit:
    rule_hit_id: str
    rule_id: str
    merge_key: str
    rule_set_version: str
    issue_type_candidate: str
    matched_text: str
    matched_clause_id: str
    line_start: int
    line_end: int
    rationale: str
    severity_score: int
    related_rule_ids: tuple[str, ...]
    related_reference_ids: tuple[str, ...]
    source_section: str
    rewrite_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuleHit":
        return cls(**payload)


@dataclass
class Finding:
    finding_id: str
    document_name: str
    problem_title: str
    page_hint: str | None
    clause_id: str
    source_section: str
    section_path: str | None
    table_or_item_label: str | None
    text_line_start: int
    text_line_end: int
    source_text: str
    issue_type: str
    risk_level: str
    severity_score: int
    confidence: str
    compliance_judgment: str
    why_it_is_risky: str
    impact_on_competition_or_performance: str
    legal_or_policy_basis: str | None
    rewrite_suggestion: str
    needs_human_review: bool
    human_review_reason: str | None
    document_structure_type: str | None = None
    risk_scope: str | None = None
    scope_reason: str | None = None
    primary_authority: str | None = None
    secondary_authorities: list[str] | None = None
    authority_key_points: str | None = None
    applicability_logic: str | None = None
    finding_origin: str = "rule"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Finding":
        return cls(**payload)


@dataclass
class ReviewResult:
    document_name: str
    review_scope: str
    jurisdiction: str | None
    review_timestamp: str
    overall_risk_summary: str
    findings: list[Finding]
    items_for_human_review: list[str]
    review_limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_name": self.document_name,
            "review_scope": self.review_scope,
            "jurisdiction": self.jurisdiction,
            "review_timestamp": self.review_timestamp,
            "overall_risk_summary": self.overall_risk_summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "items_for_human_review": self.items_for_human_review,
            "review_limitations": self.review_limitations,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReviewResult":
        return cls(
            document_name=payload["document_name"],
            review_scope=payload["review_scope"],
            jurisdiction=payload.get("jurisdiction"),
            review_timestamp=payload["review_timestamp"],
            overall_risk_summary=payload["overall_risk_summary"],
            findings=[Finding.from_dict(item) for item in payload["findings"]],
            items_for_human_review=payload.get("items_for_human_review", []),
            review_limitations=payload.get("review_limitations", []),
        )
