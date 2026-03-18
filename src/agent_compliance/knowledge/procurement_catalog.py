from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path

from agent_compliance.schemas import NormalizedDocument


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_FILE = REPO_ROOT / "data" / "procurement-catalog" / "catalogs.json"


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
class CatalogClassification:
    primary_catalog: str
    primary_catalog_name: str
    primary_domain_key: str
    secondary_catalogs: tuple[str, ...]
    secondary_catalog_names: tuple[str, ...]
    category_type: str
    catalog_confidence: float
    is_mixed_scope: bool
    catalog_evidence: tuple[str, ...]


@lru_cache(maxsize=1)
def load_procurement_catalogs() -> tuple[ProcurementCatalog, ...]:
    payload = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return tuple(
        ProcurementCatalog(
            catalog_id=item["catalog_id"],
            catalog_name=item["catalog_name"],
            domain_key=item["domain_key"],
            category_type=item["category_type"],
            domain_keywords=tuple(item.get("domain_keywords", [])),
            reasonable_requirements=tuple(item.get("reasonable_requirements", [])),
            high_risk_patterns=tuple(item.get("high_risk_patterns", [])),
            related_issue_types=tuple(item.get("related_issue_types", [])),
            preferred_analyzers=tuple(item.get("preferred_analyzers", [])),
        )
        for item in payload
    )


def _catalog_by_domain_key(domain_key: str) -> ProcurementCatalog | None:
    for catalog in load_procurement_catalogs():
        if catalog.domain_key == domain_key:
            return catalog
    return None


def classify_procurement_catalog(document: NormalizedDocument) -> CatalogClassification:
    catalogs = load_procurement_catalogs()
    title_text = f"{document.document_name} {document.source_path}".lower()
    body_text = " ".join(clause.text for clause in document.clauses[:200]).lower()
    mixed_info_markers = ("系统端口", "无缝对接", "信息化管理系统", "综合业务协同平台", "软件著作权", "智能管理系统", "资产定位")
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
    elif any(item[1].category_type != primary_catalog.category_type for item in secondary):
        is_mixed_scope = True
        category_type = "mixed"

    confidence = primary_score / max(primary_score + sum(score for score, _, _ in secondary), 1)
    evidence = tuple(dict.fromkeys([*primary_matches, *[match for _, _, matches in secondary for match in matches]]))[:8]

    return CatalogClassification(
        primary_catalog=primary_catalog.catalog_id,
        primary_catalog_name=primary_catalog.catalog_name,
        primary_domain_key=primary_domain_key,
        secondary_catalogs=tuple(item[1].catalog_id for item in secondary),
        secondary_catalog_names=tuple(item[1].catalog_name for item in secondary),
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
