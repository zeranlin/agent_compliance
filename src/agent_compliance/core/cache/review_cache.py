from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agent_compliance.core.config import detect_paths
from agent_compliance.core.schemas import ReviewResult


REVIEW_CACHE_VERSION = "v1"


def reference_snapshot_id(reference_root: Path) -> str:
    digest = hashlib.sha256()
    if not reference_root.exists():
        return "no-references"

    for path in sorted(reference_root.rglob("*.md")):
        digest.update(str(path.relative_to(reference_root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def build_review_cache_key(
    *,
    file_hash: str,
    rule_set_version: str,
    reference_snapshot: str,
    parser_mode: str = "off",
    review_pipeline_version: str = REVIEW_CACHE_VERSION,
) -> str:
    digest = hashlib.sha256()
    for value in (file_hash, rule_set_version, reference_snapshot, parser_mode, review_pipeline_version):
        digest.update(value.encode("utf-8"))
    return digest.hexdigest()[:16]


def cache_path_for_key(cache_key: str) -> Path:
    paths = detect_paths()
    root = paths.cache_root / "reviews"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{cache_key}.json"


def load_review_cache(cache_key: str) -> ReviewResult | None:
    path = cache_path_for_key(cache_key)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ReviewResult.from_dict(payload["review"])


def save_review_cache(cache_key: str, review: ReviewResult, metadata: dict[str, str]) -> Path:
    path = cache_path_for_key(cache_key)
    payload = {
        "cache_key": cache_key,
        "metadata": metadata,
        "review": review.to_dict(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
