from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from agent_compliance.core.config import detect_paths


@dataclass(frozen=True)
class IssueTypeAuthorityRecord:
    issue_type: str
    primary_reference_ids: tuple[str, ...]
    primary_clause_ids: tuple[str, ...]
    secondary_reference_ids: tuple[str, ...]
    secondary_clause_ids: tuple[str, ...]
    authority_priority: tuple[str, ...]
    reasoning_template: str
    fallback_review_topics: tuple[str, ...]
    requires_human_review_when: tuple[str, ...]


def issue_type_authority_map_path() -> Path:
    paths = detect_paths()
    return paths.repo_root / "data" / "legal-authorities" / "index" / "issue-type-authority-map.json"


def load_issue_type_authority_records() -> list[IssueTypeAuthorityRecord]:
    path = issue_type_authority_map_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records: list[IssueTypeAuthorityRecord] = []
    for item in payload.get("mappings", []):
        if not isinstance(item, dict):
            continue
        issue_type = str(item.get("issue_type", "")).strip()
        reasoning_template = str(item.get("reasoning_template", "")).strip()
        if not issue_type or not reasoning_template:
            continue
        records.append(
            IssueTypeAuthorityRecord(
                issue_type=issue_type,
                primary_reference_ids=tuple(_normalize_str_list(item.get("primary_reference_ids"))),
                primary_clause_ids=tuple(_normalize_str_list(item.get("primary_clause_ids"))),
                secondary_reference_ids=tuple(_normalize_str_list(item.get("secondary_reference_ids"))),
                secondary_clause_ids=tuple(_normalize_str_list(item.get("secondary_clause_ids"))),
                authority_priority=tuple(_normalize_str_list(item.get("authority_priority"))),
                reasoning_template=reasoning_template,
                fallback_review_topics=tuple(_normalize_str_list(item.get("fallback_review_topics"))),
                requires_human_review_when=tuple(_normalize_str_list(item.get("requires_human_review_when"))),
            )
        )
    return records


def get_issue_type_authority_record(issue_type: str) -> IssueTypeAuthorityRecord | None:
    issue_type = issue_type.strip()
    for record in load_issue_type_authority_records():
        if record.issue_type == issue_type:
            return record
    return None


def _normalize_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
