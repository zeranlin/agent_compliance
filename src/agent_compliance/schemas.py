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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PageSpan:
    page_number: int
    line_start: int
    line_end: int
    is_estimated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


@dataclass
class RuleHit:
    rule_hit_id: str
    rule_id: str
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
