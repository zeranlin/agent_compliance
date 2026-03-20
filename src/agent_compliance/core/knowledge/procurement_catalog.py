from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path

from agent_compliance.core.schemas import NormalizedDocument
from agent_compliance.core.knowledge.review_domain_map import load_review_domain_map, review_domain_map_by_catalog_id


REPO_ROOT = Path(__file__).resolve().parents[4]
CATALOG_FILE = REPO_ROOT / "data" / "procurement-catalog" / "catalogs.json"
FULL_CATALOG_FILE = REPO_ROOT / "data" / "procurement-catalog" / "catalogs-full.json"


@dataclass(frozen=True)
class ProcurementCatalog:
    catalog_id: str
    catalog_name: str
    domain_key: str
    category_type: str
    domain_keywords: tuple[str, ...]
    reasonable_requirements: tuple[str, ...]
    high_risk_patterns: tuple[str, ...]
    related_issue_types: tuple[str, ...]
    preferred_analyzers: tuple[str, ...]


@dataclass(frozen=True)
class FullCatalogEntry:
    catalog_code: str
    catalog_name: str
    category_type: str
    level: int
    parent_code: str


def _clean_catalog_name(name: str) -> str:
    cleaned = name.strip()
    for marker in (" ——", "  ", "\t"):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()
    if " " in cleaned:
        cleaned = cleaned.split(" ", 1)[0].strip()
    return cleaned


@dataclass(frozen=True)
class CatalogClassification:
    primary_catalog: str
    primary_catalog_name: str
    primary_domain_key: str
    secondary_catalogs: tuple[str, ...]
    secondary_catalog_names: tuple[str, ...]
    primary_mapped_catalog_codes: tuple[str, ...]
    primary_mapped_catalog_prefixes: tuple[str, ...]
    secondary_mapped_catalog_codes: tuple[str, ...]
    secondary_mapped_catalog_prefixes: tuple[str, ...]
    category_type: str
    catalog_confidence: float
    is_mixed_scope: bool
    catalog_evidence: tuple[str, ...]


@lru_cache(maxsize=1)
def load_procurement_catalogs() -> tuple[ProcurementCatalog, ...]:
    payload = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    review_domain_map = {entry.catalog_id: entry for entry in load_review_domain_map()}
    full_catalog_names = full_catalog_names_by_code_or_prefix()
    return tuple(
        ProcurementCatalog(
            catalog_id=item["catalog_id"],
            catalog_name=item["catalog_name"],
            domain_key=item["domain_key"],
            category_type=item["category_type"],
            domain_keywords=tuple(
                dict.fromkeys(
                    [
                        *item.get("domain_keywords", []),
                        *(
                            review_domain_map.get(item["catalog_id"]).keyword_fallbacks
                            if review_domain_map.get(item["catalog_id"]) is not None
                            else ()
                        ),
                        *full_catalog_names.get(item["catalog_id"], ()),
                    ]
                )
            ),
            reasonable_requirements=tuple(item.get("reasonable_requirements", [])),
            high_risk_patterns=tuple(item.get("high_risk_patterns", [])),
            related_issue_types=tuple(item.get("related_issue_types", [])),
            preferred_analyzers=tuple(item.get("preferred_analyzers", [])),
        )
        for item in payload
    )


@lru_cache(maxsize=1)
def load_full_catalog_entries() -> tuple[FullCatalogEntry, ...]:
    payload = json.loads(FULL_CATALOG_FILE.read_text(encoding="utf-8"))
    return tuple(
        FullCatalogEntry(
            catalog_code=item["catalog_code"],
            catalog_name=item["catalog_name"],
            category_type=item["category_type"],
            level=int(item["level"]),
            parent_code=item["parent_code"],
        )
        for item in payload.get("entries", [])
    )


@lru_cache(maxsize=1)
def full_catalog_names_by_code_or_prefix() -> dict[str, tuple[str, ...]]:
    full_entries = load_full_catalog_entries()
    review_map = load_review_domain_map()
    resolved: dict[str, tuple[str, ...]] = {}
    for entry in review_map:
        names: list[str] = []
        exact_codes = set(entry.mapped_catalog_codes)
        prefixes = tuple(entry.mapped_catalog_prefixes)
        for full_entry in full_entries:
            if full_entry.catalog_code in exact_codes:
                names.append(_clean_catalog_name(full_entry.catalog_name))
                continue
            if prefixes and any(full_entry.catalog_code.startswith(prefix) for prefix in prefixes):
                if full_entry.level <= 4:
                    names.append(_clean_catalog_name(full_entry.catalog_name))
        resolved[entry.catalog_id] = tuple(dict.fromkeys(names))[:24]
    return resolved


def _catalog_by_domain_key(domain_key: str) -> ProcurementCatalog | None:
    for catalog in load_procurement_catalogs():
        if catalog.domain_key == domain_key:
            return catalog
    return None


def _mapped_codes_and_prefixes(catalog_ids: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    codes: list[str] = []
    prefixes: list[str] = []
    for catalog_id in catalog_ids:
        entry = review_domain_map_by_catalog_id(catalog_id)
        if entry is None:
            continue
        for code in entry.mapped_catalog_codes:
            if code not in codes:
                codes.append(code)
        for prefix in entry.mapped_catalog_prefixes:
            if prefix not in prefixes:
                prefixes.append(prefix)
    return tuple(codes), tuple(prefixes)


def classify_procurement_catalog(document: NormalizedDocument) -> CatalogClassification:
    catalogs = load_procurement_catalogs()
    title_text = f"{document.document_name} {document.source_path}".lower()
    body_text = " ".join(clause.text for clause in document.clauses[:200]).lower()
    mixed_info_markers = (
        "系统端口",
        "无缝对接",
        "信息化管理系统",
        "综合业务协同平台",
        "软件著作权",
        "智能管理系统",
        "资产定位",
        "二维码报修",
        "OTA",
        "远程升级",
        "智能显示",
    )
    mixed_device_markers = ("自动化调剂", "发药机", "自动化设备", "设备需求参数", "设备接口")

    scored: list[tuple[int, int, ProcurementCatalog, tuple[str, ...]]] = []
    for catalog in catalogs:
        title_matches = tuple(keyword for keyword in catalog.domain_keywords if keyword.lower() in title_text)
        body_matches = tuple(keyword for keyword in catalog.domain_keywords if keyword.lower() in body_text)
        unique_matches = tuple(dict.fromkeys([*title_matches, *body_matches]))
        if not unique_matches:
            continue
        score = len(title_matches) * 3 + len(body_matches)
        scored.append((score, len(title_matches), catalog, unique_matches))

    scored.sort(key=lambda item: (-item[0], -item[1], item[2].catalog_id))

    if not scored:
        return CatalogClassification(
            primary_catalog="CAT-GENERAL",
            primary_catalog_name="综合型政府采购",
            primary_domain_key="general",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=(),
            primary_mapped_catalog_prefixes=(),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="mixed",
            catalog_confidence=0.0,
            is_mixed_scope=False,
            catalog_evidence=(),
        )

    primary_score, primary_title_match_count, primary_catalog, primary_matches = scored[0]
    if primary_title_match_count == 0 and primary_score < 3:
        return CatalogClassification(
            primary_catalog="CAT-GENERAL",
            primary_catalog_name="综合型政府采购",
            primary_domain_key="general",
            secondary_catalogs=(),
            secondary_catalog_names=(),
            primary_mapped_catalog_codes=(),
            primary_mapped_catalog_prefixes=(),
            secondary_mapped_catalog_codes=(),
            secondary_mapped_catalog_prefixes=(),
            category_type="mixed",
            catalog_confidence=0.0,
            is_mixed_scope=False,
            catalog_evidence=primary_matches,
        )
    secondary = [
        (score, catalog, matches)
        for score, _title_count, catalog, matches in scored[1:]
        if score >= max(2, primary_score - 2)
    ]

    is_mixed_scope = bool(secondary)
    primary_domain_key = primary_catalog.domain_key
    category_type = primary_catalog.category_type

    if primary_catalog.domain_key == "medical_tcm" and (
        any(item[1].domain_key in {"information_system", "equipment_installation", "medical_device_goods"} for item in secondary)
        or (any(marker in body_text for marker in mixed_info_markers) and any(marker in body_text for marker in mixed_device_markers))
    ):
        primary_domain_key = "medical_tcm_mixed"
        is_mixed_scope = True
        category_type = "mixed"
        info_catalog = _catalog_by_domain_key("information_system")
        if info_catalog is not None and info_catalog.catalog_name not in [item[1].catalog_name for item in secondary]:
            secondary.append((2, info_catalog, tuple(marker for marker in mixed_info_markers if marker in body_text)[:2]))
    elif primary_catalog.domain_key in {"furniture_goods", "signage_printing_service"} and (
        any(item[1].domain_key == "information_system" for item in secondary)
        or any(marker in body_text for marker in mixed_info_markers)
    ):
        is_mixed_scope = True
        category_type = "mixed"
    elif primary_catalog.domain_key == "sports_facility_goods" and (
        any(item[1].domain_key == "information_system" for item in secondary)
        or any(marker in body_text for marker in mixed_info_markers)
    ):
        is_mixed_scope = True
        category_type = "mixed"
    elif any(item[1].category_type != primary_catalog.category_type for item in secondary):
        is_mixed_scope = True
        category_type = "mixed"

    confidence = primary_score / max(primary_score + sum(score for score, _, _ in secondary), 1)
    evidence = tuple(dict.fromkeys([*primary_matches, *[match for _, _, matches in secondary for match in matches]]))[:8]
    primary_codes, primary_prefixes = _mapped_codes_and_prefixes((primary_catalog.catalog_id,))
    secondary_codes, secondary_prefixes = _mapped_codes_and_prefixes([item[1].catalog_id for item in secondary])

    return CatalogClassification(
        primary_catalog=primary_catalog.catalog_id,
        primary_catalog_name=primary_catalog.catalog_name,
        primary_domain_key=primary_domain_key,
        secondary_catalogs=tuple(item[1].catalog_id for item in secondary),
        secondary_catalog_names=tuple(item[1].catalog_name for item in secondary),
        primary_mapped_catalog_codes=primary_codes,
        primary_mapped_catalog_prefixes=primary_prefixes,
        secondary_mapped_catalog_codes=secondary_codes,
        secondary_mapped_catalog_prefixes=secondary_prefixes,
        category_type=category_type,
        catalog_confidence=round(confidence, 2),
        is_mixed_scope=is_mixed_scope,
        catalog_evidence=evidence,
    )


def classification_has_domain(classification: CatalogClassification | None, domain_key: str) -> bool:
    if classification is None:
        return False
    if classification.primary_domain_key == domain_key:
        return True
    if classification.primary_domain_key == "medical_tcm_mixed" and domain_key in {
        "medical_tcm",
        "medical_device_goods",
        "information_system",
        "equipment_installation",
    }:
        return True
    catalogs = {catalog.catalog_id: catalog for catalog in load_procurement_catalogs()}
    return any(catalogs.get(catalog_id) and catalogs[catalog_id].domain_key == domain_key for catalog_id in classification.secondary_catalogs)


def classification_has_catalog_prefix(classification: CatalogClassification | None, prefix: str) -> bool:
    if classification is None:
        return False
    return any(code.startswith(prefix) for code in classification.primary_mapped_catalog_codes) or any(
        mapped_prefix.startswith(prefix) or prefix.startswith(mapped_prefix)
        for mapped_prefix in (*classification.primary_mapped_catalog_prefixes, *classification.secondary_mapped_catalog_prefixes)
    )
