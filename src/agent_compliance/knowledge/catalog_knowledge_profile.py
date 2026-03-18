from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path

from agent_compliance.knowledge.procurement_catalog import CatalogClassification


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_KNOWLEDGE_FILE = REPO_ROOT / "data" / "procurement-catalog" / "catalog-knowledge-profiles.json"


@dataclass(frozen=True)
class CatalogKnowledgeProfile:
    catalog_id: str
    catalog_name: str
    review_domain_key: str
    category_type: str
    reasonable_requirements: tuple[str, ...]
    high_risk_patterns: tuple[str, ...]
    common_mismatch_clues: tuple[str, ...]
    boundary_notes: str
    related_issue_types: tuple[str, ...]
    preferred_analyzers: tuple[str, ...]


@lru_cache(maxsize=1)
def load_catalog_knowledge_profiles() -> tuple[CatalogKnowledgeProfile, ...]:
    payload = json.loads(CATALOG_KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    return tuple(
        CatalogKnowledgeProfile(
            catalog_id=item["catalog_id"],
            catalog_name=item["catalog_name"],
            review_domain_key=item["review_domain_key"],
            category_type=item["category_type"],
            reasonable_requirements=tuple(item.get("reasonable_requirements", [])),
            high_risk_patterns=tuple(item.get("high_risk_patterns", [])),
            common_mismatch_clues=tuple(item.get("common_mismatch_clues", [])),
            boundary_notes=item.get("boundary_notes", ""),
            related_issue_types=tuple(item.get("related_issue_types", [])),
            preferred_analyzers=tuple(item.get("preferred_analyzers", [])),
        )
        for item in payload.get("profiles", [])
    )


def catalog_knowledge_profile_by_catalog_id(catalog_id: str) -> CatalogKnowledgeProfile | None:
    for profile in load_catalog_knowledge_profiles():
        if profile.catalog_id == catalog_id:
            return profile
    return None


def catalog_knowledge_profiles_for_classification(
    classification: CatalogClassification | None,
) -> tuple[CatalogKnowledgeProfile, ...]:
    if classification is None or not classification.primary_catalog:
        return ()
    profiles: list[CatalogKnowledgeProfile] = []
    seen: set[str] = set()
    for catalog_id in (classification.primary_catalog, *classification.secondary_catalogs):
        profile = catalog_knowledge_profile_by_catalog_id(catalog_id)
        if profile is None or profile.catalog_id in seen:
            continue
        profiles.append(profile)
        seen.add(profile.catalog_id)
    return tuple(profiles)
