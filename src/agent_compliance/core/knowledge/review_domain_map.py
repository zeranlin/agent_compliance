from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
REVIEW_DOMAIN_MAP_FILE = REPO_ROOT / "data" / "procurement-catalog" / "review-domain-map.json"


@dataclass(frozen=True)
class ReviewDomainMapEntry:
    catalog_id: str
    review_domain_key: str
    review_domain_name: str
    category_type: str
    mapped_catalog_codes: tuple[str, ...]
    mapped_catalog_prefixes: tuple[str, ...]
    keyword_fallbacks: tuple[str, ...]
    coverage_note: str
    preferred_analyzers: tuple[str, ...]


@lru_cache(maxsize=1)
def load_review_domain_map() -> tuple[ReviewDomainMapEntry, ...]:
    payload = json.loads(REVIEW_DOMAIN_MAP_FILE.read_text(encoding="utf-8"))
    return tuple(
        ReviewDomainMapEntry(
            catalog_id=item["catalog_id"],
            review_domain_key=item["review_domain_key"],
            review_domain_name=item["review_domain_name"],
            category_type=item["category_type"],
            mapped_catalog_codes=tuple(item.get("mapped_catalog_codes", [])),
            mapped_catalog_prefixes=tuple(item.get("mapped_catalog_prefixes", [])),
            keyword_fallbacks=tuple(item.get("keyword_fallbacks", [])),
            coverage_note=item.get("coverage_note", ""),
            preferred_analyzers=tuple(item.get("preferred_analyzers", [])),
        )
        for item in payload.get("entries", [])
    )


def review_domain_map_by_domain_key(domain_key: str) -> ReviewDomainMapEntry | None:
    for entry in load_review_domain_map():
        if entry.review_domain_key == domain_key:
            return entry
    return None


def review_domain_map_by_catalog_id(catalog_id: str) -> ReviewDomainMapEntry | None:
    for entry in load_review_domain_map():
        if entry.catalog_id == catalog_id:
            return entry
    return None
