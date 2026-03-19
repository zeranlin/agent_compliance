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
    core_delivery_capabilities: tuple[str, ...]
    high_risk_patterns: tuple[str, ...]
    scoring_risk_markers: tuple[str, ...]
    scoring_mismatch_markers: tuple[str, ...]
    scoring_theme_markers: tuple[str, ...]
    scoring_evidence_markers: tuple[str, ...]
    commercial_lifecycle_markers: tuple[str, ...]
    common_mismatch_clues: tuple[str, ...]
    domain_mismatch_markers: tuple[str, ...]
    template_scope_markers: tuple[str, ...]
    mixed_scope_markers: tuple[str, ...]
    mixed_scope_core_markers: tuple[str, ...]
    mixed_scope_support_markers: tuple[str, ...]
    mixed_scope_out_of_scope_markers: tuple[str, ...]
    mixed_scope_hard_mismatch_markers: tuple[str, ...]
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
            core_delivery_capabilities=tuple(item.get("core_delivery_capabilities", item.get("reasonable_requirements", []))),
            high_risk_patterns=tuple(item.get("high_risk_patterns", [])),
            scoring_risk_markers=tuple(item.get("scoring_risk_markers", item.get("high_risk_patterns", []))),
            scoring_mismatch_markers=tuple(item.get("scoring_mismatch_markers", item.get("domain_mismatch_markers", item.get("common_mismatch_clues", [])))),
            scoring_theme_markers=tuple(item.get("scoring_theme_markers", item.get("core_delivery_capabilities", item.get("reasonable_requirements", [])))),
            scoring_evidence_markers=tuple(item.get("scoring_evidence_markers", [])),
            commercial_lifecycle_markers=tuple(item.get("commercial_lifecycle_markers", [])),
            common_mismatch_clues=tuple(item.get("common_mismatch_clues", [])),
            domain_mismatch_markers=tuple(item.get("domain_mismatch_markers", item.get("common_mismatch_clues", []))),
            template_scope_markers=tuple(item.get("template_scope_markers", [])),
            mixed_scope_markers=tuple(item.get("mixed_scope_markers", [])),
            mixed_scope_core_markers=tuple(item.get("mixed_scope_core_markers", item.get("core_delivery_capabilities", item.get("reasonable_requirements", [])))),
            mixed_scope_support_markers=tuple(item.get("mixed_scope_support_markers", [])),
            mixed_scope_out_of_scope_markers=tuple(item.get("mixed_scope_out_of_scope_markers", item.get("mixed_scope_markers", []))),
            mixed_scope_hard_mismatch_markers=tuple(item.get("mixed_scope_hard_mismatch_markers", item.get("mixed_scope_out_of_scope_markers", item.get("mixed_scope_markers", [])))),
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


def catalog_domain_mismatch_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.domain_mismatch_markers)
    return tuple(dict.fromkeys(values))


def catalog_template_scope_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.template_scope_markers)
    return tuple(dict.fromkeys(values))


def catalog_mixed_scope_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.mixed_scope_markers)
    return tuple(dict.fromkeys(values))


def catalog_mixed_scope_core_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.mixed_scope_core_markers)
    return tuple(dict.fromkeys(values))


def catalog_mixed_scope_out_of_scope_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.mixed_scope_out_of_scope_markers)
    return tuple(dict.fromkeys(values))


def catalog_mixed_scope_support_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.mixed_scope_support_markers)
    return tuple(dict.fromkeys(values))


def catalog_mixed_scope_hard_mismatch_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.mixed_scope_hard_mismatch_markers)
    return tuple(dict.fromkeys(values))


def catalog_core_delivery_capabilities_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.core_delivery_capabilities)
    return tuple(dict.fromkeys(values))


def catalog_scoring_risk_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.scoring_risk_markers)
    return tuple(dict.fromkeys(values))


def catalog_scoring_mismatch_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.scoring_mismatch_markers)
    return tuple(dict.fromkeys(values))


def catalog_scoring_theme_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.scoring_theme_markers)
    return tuple(dict.fromkeys(values))


def catalog_scoring_evidence_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.scoring_evidence_markers)
    return tuple(dict.fromkeys(values))


def catalog_commercial_lifecycle_markers_for_classification(
    classification: CatalogClassification | None,
) -> tuple[str, ...]:
    values: list[str] = []
    for profile in catalog_knowledge_profiles_for_classification(classification):
        values.extend(profile.commercial_lifecycle_markers)
    return tuple(dict.fromkeys(values))
