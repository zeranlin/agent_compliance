from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from agent_compliance.config import detect_paths


@dataclass(frozen=True)
class LegalClauseRecord:
    clause_id: str
    reference_id: str
    doc_title: str
    doc_no: str | None
    authority_level: str | None
    validity_status: str | None
    chapter_label: str | None
    article_label: str | None
    clause_text: str
    keywords: tuple[str, ...]
    review_topics: tuple[str, ...]
    source_url: str | None
    canonical_registry_url: str | None
    last_verified: str | None


def clause_index_path() -> Path:
    paths = detect_paths()
    return paths.repo_root / "data" / "legal-authorities" / "index" / "clause-index.json"


def load_legal_clause_records() -> list[LegalClauseRecord]:
    path = clause_index_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records: list[LegalClauseRecord] = []
    for item in payload.get("clauses", []):
        if not isinstance(item, dict):
            continue
        clause_id = str(item.get("clause_id", "")).strip()
        reference_id = str(item.get("reference_id", "")).strip()
        clause_text = str(item.get("clause_text", "")).strip()
        doc_title = str(item.get("doc_title", "")).strip()
        if not clause_id or not reference_id or not clause_text or not doc_title:
            continue
        records.append(
            LegalClauseRecord(
                clause_id=clause_id,
                reference_id=reference_id,
                doc_title=doc_title,
                doc_no=_optional_text(item.get("doc_no")),
                authority_level=_optional_text(item.get("authority_level")),
                validity_status=_optional_text(item.get("validity_status")),
                chapter_label=_optional_text(item.get("chapter_label")),
                article_label=_optional_text(item.get("article_label")),
                clause_text=clause_text,
                keywords=tuple(_normalize_str_list(item.get("keywords"))),
                review_topics=tuple(_normalize_str_list(item.get("review_topics"))),
                source_url=_optional_text(item.get("source_url")),
                canonical_registry_url=_optional_text(item.get("canonical_registry_url")),
                last_verified=_optional_text(item.get("last_verified")),
            )
        )
    return records


def find_legal_clauses(
    *,
    reference_id: str | None = None,
    review_topic: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
) -> list[LegalClauseRecord]:
    records = load_legal_clause_records()
    results: list[LegalClauseRecord] = []
    review_topic = (review_topic or "").strip()
    keyword = (keyword or "").strip()
    for record in records:
        if reference_id and record.reference_id != reference_id:
            continue
        if review_topic and review_topic not in record.review_topics:
            continue
        if keyword and keyword not in record.clause_text and keyword not in "".join(record.keywords):
            continue
        results.append(record)
    return results[:limit]


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _normalize_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
