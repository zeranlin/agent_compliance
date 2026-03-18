from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_INDEX_PATH = REPO_ROOT / "data" / "legal-authorities" / "index" / "authorities.json"
OUTPUT_PATH = REPO_ROOT / "data" / "legal-authorities" / "index" / "clause-index.json"

CHAPTER_RE = re.compile(r"^(第[一二三四五六七八九十百零]+章)\s*(.*)$")
ARTICLE_RE = re.compile(r"^(第[一二三四五六七八九十百零]+条)\s*(.*)$")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+、)\s*(.*)$")
PAGE_NUMBER_RE = re.compile(r"^\d+$")


def main() -> None:
    payload = json.loads(AUTHORITY_INDEX_PATH.read_text(encoding="utf-8"))
    clauses: list[dict[str, object]] = []
    for authority in payload.get("authorities", []):
        if not isinstance(authority, dict):
            continue
        clauses.extend(_extract_authority_clauses(authority))
    output = {"version": "v1", "clause_count": len(clauses), "clauses": clauses}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(clauses)} clauses to {OUTPUT_PATH}")


def _extract_authority_clauses(authority: dict[str, object]) -> list[dict[str, object]]:
    reference_id = str(authority.get("reference_id", "")).strip()
    title = str(authority.get("reference_title", "")).strip()
    normalized_path = str(authority.get("normalized_text_path", "")).strip()
    raw_metadata_path = str(authority.get("raw_metadata_path", "")).strip()
    if not reference_id or not title or not normalized_path:
        return []
    text_path = REPO_ROOT / normalized_path
    if not text_path.exists():
        return []
    metadata = _load_metadata(raw_metadata_path)
    text = text_path.read_text(encoding="utf-8")
    if reference_id == "LEGAL-001":
        return _extract_article_style_clauses(reference_id, title, text, authority, metadata)
    if reference_id == "LEGAL-002":
        return _extract_section_style_clauses(reference_id, title, text, authority, metadata)
    return _extract_paragraph_style_clauses(reference_id, title, text, authority, metadata)


def _extract_article_style_clauses(
    reference_id: str,
    title: str,
    text: str,
    authority: dict[str, object],
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    clauses: list[dict[str, object]] = []
    chapter_label: str | None = None
    current_article: str | None = None
    current_lines: list[str] = []
    article_index = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or PAGE_NUMBER_RE.match(line) or line == "附件：":
            continue
        chapter_match = CHAPTER_RE.match(line)
        if chapter_match:
            if current_article and current_lines:
                article_index += 1
                clauses.append(
                    _make_clause_record(
                        reference_id=reference_id,
                        title=title,
                        authority=authority,
                        metadata=metadata,
                        clause_id=f"{reference_id}-ART-{article_index:03d}",
                        chapter_label=chapter_label,
                        article_label=current_article,
                        clause_text="".join(current_lines).strip(),
                    )
                )
            chapter_label = chapter_match.group(1)
            current_article = None
            current_lines = []
            continue
        article_match = ARTICLE_RE.match(line)
        if article_match:
            if current_article and current_lines:
                article_index += 1
                clauses.append(
                    _make_clause_record(
                        reference_id=reference_id,
                        title=title,
                        authority=authority,
                        metadata=metadata,
                        clause_id=f"{reference_id}-ART-{article_index:03d}",
                        chapter_label=chapter_label,
                        article_label=current_article,
                        clause_text="".join(current_lines).strip(),
                    )
                )
            current_article = article_match.group(1)
            current_lines = [article_match.group(2).strip()]
            continue
        if current_article:
            current_lines.append(line)
    if current_article and current_lines:
        article_index += 1
        clauses.append(
            _make_clause_record(
                reference_id=reference_id,
                title=title,
                authority=authority,
                metadata=metadata,
                clause_id=f"{reference_id}-ART-{article_index:03d}",
                chapter_label=chapter_label,
                article_label=current_article,
                clause_text="".join(current_lines).strip(),
            )
        )
    return clauses


def _extract_section_style_clauses(
    reference_id: str,
    title: str,
    text: str,
    authority: dict[str, object],
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    clauses: list[dict[str, object]] = []
    current_section: str | None = None
    current_lines: list[str] = []
    section_index = 0
    started = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(".TRS_Editor"):
            continue
        section_match = SECTION_RE.match(line)
        if section_match:
            started = True
            if current_section and current_lines:
                section_index += 1
                clauses.append(
                    _make_clause_record(
                        reference_id=reference_id,
                        title=title,
                        authority=authority,
                        metadata=metadata,
                        clause_id=f"{reference_id}-SEC-{section_index:03d}",
                        chapter_label=None,
                        article_label=current_section,
                        clause_text="".join(current_lines).strip(),
                    )
                )
            current_section = section_match.group(1).rstrip("、")
            current_lines = [section_match.group(2).strip()]
            continue
        if not started:
            continue
        if current_section:
            current_lines.append(line)
    if current_section and current_lines:
        section_index += 1
        clauses.append(
            _make_clause_record(
                reference_id=reference_id,
                title=title,
                authority=authority,
                metadata=metadata,
                clause_id=f"{reference_id}-SEC-{section_index:03d}",
                chapter_label=None,
                article_label=current_section,
                clause_text="".join(current_lines).strip(),
            )
        )
    return clauses


def _extract_paragraph_style_clauses(
    reference_id: str,
    title: str,
    text: str,
    authority: dict[str, object],
    metadata: dict[str, object],
) -> list[dict[str, object]]:
    clauses: list[dict[str, object]] = []
    buffer: list[str] = []
    paragraph_index = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if buffer:
                paragraph_index += 1
                clauses.append(
                    _make_clause_record(
                        reference_id=reference_id,
                        title=title,
                        authority=authority,
                        metadata=metadata,
                        clause_id=f"{reference_id}-PAR-{paragraph_index:03d}",
                        chapter_label=None,
                        article_label=f"段落{paragraph_index}",
                        clause_text="".join(buffer).strip(),
                    )
                )
                buffer = []
            continue
        buffer.append(line)
    if buffer:
        paragraph_index += 1
        clauses.append(
            _make_clause_record(
                reference_id=reference_id,
                title=title,
                authority=authority,
                metadata=metadata,
                clause_id=f"{reference_id}-PAR-{paragraph_index:03d}",
                chapter_label=None,
                article_label=f"段落{paragraph_index}",
                clause_text="".join(buffer).strip(),
            )
        )
    return clauses


def _make_clause_record(
    *,
    reference_id: str,
    title: str,
    authority: dict[str, object],
    metadata: dict[str, object],
    clause_id: str,
    chapter_label: str | None,
    article_label: str | None,
    clause_text: str,
) -> dict[str, object]:
    return {
        "clause_id": clause_id,
        "reference_id": reference_id,
        "doc_title": title,
        "doc_no": metadata.get("doc_no", ""),
        "authority_level": metadata.get("authority_level", ""),
        "validity_status": metadata.get("validity_status", ""),
        "chapter_label": chapter_label,
        "article_label": article_label,
        "clause_text": clause_text,
        "keywords": _keywords_for_clause(title, chapter_label, article_label, clause_text),
        "review_topics": authority.get("review_topics", []),
        "source_url": metadata.get("source_url", ""),
        "canonical_registry_url": metadata.get("canonical_registry_url", ""),
        "last_verified": metadata.get("last_verified", ""),
    }


def _keywords_for_clause(
    title: str,
    chapter_label: str | None,
    article_label: str | None,
    clause_text: str,
) -> list[str]:
    seeds = [title, chapter_label or "", article_label or ""]
    shortlist = [
        "资格条件",
        "供应商资格",
        "评审因素",
        "评分项",
        "采购需求",
        "商务要求",
        "技术要求",
        "验收",
        "付款",
        "合同",
        "政府采购政策",
        "中小企业",
        "履约能力",
        "量化指标",
        "需求调查",
        "采购实施计划",
        "竞争范围",
    ]
    content = clause_text[:200]
    for token in shortlist:
        if token in content:
            seeds.append(token)
    normalized: list[str] = []
    for seed in seeds:
        text = str(seed).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _load_metadata(relative_path: str) -> dict[str, object]:
    if not relative_path:
        return {}
    path = REPO_ROOT / relative_path
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    main()
