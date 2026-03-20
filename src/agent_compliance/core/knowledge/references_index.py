from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path

from agent_compliance.core.config import detect_paths


@dataclass(frozen=True)
class ReferenceRecord:
    reference_id: str
    title: str
    path: str
    source_org: str | None
    source_url: str | None
    review_topics: tuple[str, ...]
    content: str
    content_source: str | None = None


def list_reference_files() -> list[str]:
    paths = detect_paths()
    reference_root = paths.repo_root / "docs" / "references"
    return sorted(str(path.relative_to(paths.repo_root)) for path in reference_root.rglob("*.md"))


def index_exists() -> bool:
    paths = detect_paths()
    return (paths.repo_root / "docs" / "references" / "reference-index.md").exists()


def load_reference_records() -> list[ReferenceRecord]:
    paths = detect_paths()
    records: list[ReferenceRecord] = []
    raw_authority_index = _load_authority_index(paths.repo_root)
    for path in (paths.repo_root / "docs" / "references").rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        title = _extract_title(content) or path.stem
        metadata = _extract_metadata(content)
        reference_id = metadata.get("reference_id", "")
        authority_entry = raw_authority_index.get(reference_id, {})
        normalized_content = _load_normalized_authority_text(paths.repo_root, authority_entry.get("normalized_text_path"))
        record = ReferenceRecord(
            reference_id=reference_id,
            title=title,
            path=str(path.relative_to(paths.repo_root)),
            source_org=metadata.get("source_org"),
            source_url=metadata.get("source_url"),
            review_topics=_split_topics(metadata.get("review_topics")),
            content=_merge_reference_content(content, normalized_content),
            content_source="normalized_authority_text" if normalized_content else "reference_markdown",
        )
        records.append(record)
    return records


def find_references(
    reference_ids: tuple[str, ...] = (),
    rule_ids: tuple[str, ...] = (),
    issue_type: str | None = None,
    limit: int = 3,
) -> list[ReferenceRecord]:
    scored: list[tuple[int, ReferenceRecord]] = []
    for record in load_reference_records():
        score = 0
        if record.reference_id and record.reference_id in reference_ids:
            score += 10
        if any(rule_id and rule_id in record.content for rule_id in rule_ids):
            score += 5
        if issue_type and any(issue_type_fragment(issue_type) in topic for topic in record.review_topics):
            score += 3
        if score:
            scored.append((score, record))

    scored.sort(key=lambda item: (-item[0], item[1].reference_id, item[1].title))
    return [record for _, record in scored[:limit]]


def _extract_title(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _extract_metadata(content: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in content.splitlines():
        match = re.match(r"- `([^`]+)`: `?(.*?)`?$", line.strip())
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata


def _load_authority_index(repo_root: Path) -> dict[str, dict[str, str]]:
    index_path = repo_root / "data" / "legal-authorities" / "index" / "authorities.json"
    if not index_path.exists():
        return {}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    records: dict[str, dict[str, str]] = {}
    for item in payload.get("authorities", []):
        reference_id = str(item.get("reference_id", "")).strip()
        if not reference_id:
            continue
        records[reference_id] = {
            "normalized_text_path": str(item.get("normalized_text_path", "")).strip(),
        }
    return records


def _load_normalized_authority_text(repo_root: Path, relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    path = repo_root / relative_path
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def _merge_reference_content(markdown_content: str, normalized_content: str | None) -> str:
    if not normalized_content:
        return markdown_content
    return f"{markdown_content}\n\n## 离线标准化法规文本\n\n{normalized_content}\n"


def _split_topics(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def issue_type_fragment(issue_type: str) -> str:
    fragments = {
        "geographic_restriction": "属地",
        "personnel_restriction": "资格条件",
        "excessive_supplier_qualification": "资格条件",
        "qualification_domain_mismatch": "资格条件",
        "irrelevant_certification_or_award": "奖项",
        "duplicative_scoring_advantage": "评分",
        "scoring_content_mismatch": "评分",
        "ambiguous_requirement": "主观评分",
        "narrow_technical_parameter": "采购需求",
        "technical_justification_needed": "采购需求",
        "unclear_acceptance_standard": "验收",
        "one_sided_commercial_term": "付款",
        "payment_acceptance_linkage": "付款",
        "template_mismatch": "采购需求",
        "other": "采购需求",
    }
    return fragments.get(issue_type, issue_type)
