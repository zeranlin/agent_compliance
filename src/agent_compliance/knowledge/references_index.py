from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from agent_compliance.config import detect_paths


@dataclass(frozen=True)
class ReferenceRecord:
    reference_id: str
    title: str
    path: str
    source_org: str | None
    source_url: str | None
    review_topics: tuple[str, ...]
    content: str


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
    for path in (paths.repo_root / "docs" / "references").rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        title = _extract_title(content) or path.stem
        metadata = _extract_metadata(content)
        record = ReferenceRecord(
            reference_id=metadata.get("reference_id", ""),
            title=title,
            path=str(path.relative_to(paths.repo_root)),
            source_org=metadata.get("source_org"),
            source_url=metadata.get("source_url"),
            review_topics=_split_topics(metadata.get("review_topics")),
            content=content,
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


def _split_topics(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def issue_type_fragment(issue_type: str) -> str:
    fragments = {
        "geographic_restriction": "属地",
        "personnel_restriction": "资格条件",
        "excessive_supplier_qualification": "资格条件",
        "irrelevant_certification_or_award": "奖项",
        "duplicative_scoring_advantage": "评分",
        "ambiguous_requirement": "主观评分",
        "narrow_technical_parameter": "采购需求",
        "technical_justification_needed": "采购需求",
        "unclear_acceptance_standard": "验收",
        "one_sided_commercial_term": "付款",
        "payment_acceptance_linkage": "付款",
        "other": "采购需求",
    }
    return fragments.get(issue_type, issue_type)
