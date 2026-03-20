from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path

from agent_compliance.core.config import detect_paths
from itertools import chain
from agent_compliance.agents.compliance_review.rules.contract_rules import RULES as CONTRACT_RULES
from agent_compliance.agents.compliance_review.rules.qualification_rules import RULES as QUALIFICATION_RULES
from agent_compliance.agents.compliance_review.rules.scoring_rules import RULES as SCORING_RULES
from agent_compliance.agents.compliance_review.rules.base import RuleDefinition
from agent_compliance.agents.compliance_review.rules.technical_rules import RULES as TECHNICAL_RULES


ALL_RULES = list(chain(QUALIFICATION_RULES, SCORING_RULES, TECHNICAL_RULES, CONTRACT_RULES))


@dataclass(frozen=True)
class RuleRegistryEntry:
    rule_id: str
    issue_type: str
    rule_family: str
    source_section: str
    merge_key: str
    governance_tier: str
    rule_status: str
    enabled_by_default: bool
    default_priority: int
    related_reference_ids: tuple[str, ...]


@dataclass(frozen=True)
class RulePriorityProfile:
    version: str
    default_family_priorities: dict[str, int]
    default_issue_type_adjustments: dict[str, int]
    default_rule_adjustments: dict[str, int]
    domain_profiles: dict[str, dict[str, object]]


def rule_priority_profile_path() -> Path:
    return detect_paths().repo_root / "data" / "rule-governance" / "rule-priority-profile.json"


@lru_cache(maxsize=1)
def load_rule_priority_profile() -> RulePriorityProfile:
    path = rule_priority_profile_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    default = payload.get("default", {})
    return RulePriorityProfile(
        version=str(payload.get("version", "v1")),
        default_family_priorities={str(key): int(value) for key, value in default.get("family_priorities", {}).items()},
        default_issue_type_adjustments={str(key): int(value) for key, value in default.get("issue_type_adjustments", {}).items()},
        default_rule_adjustments={str(key): int(value) for key, value in default.get("rule_adjustments", {}).items()},
        domain_profiles={
            str(key): {
                "family_priorities": {str(k): int(v) for k, v in value.get("family_priorities", {}).items()},
                "issue_type_adjustments": {str(k): int(v) for k, v in value.get("issue_type_adjustments", {}).items()},
                "rule_adjustments": {str(k): int(v) for k, v in value.get("rule_adjustments", {}).items()},
                "disabled_rule_ids": tuple(str(item) for item in value.get("disabled_rule_ids", []) if str(item).strip()),
                "disabled_issue_types": tuple(str(item) for item in value.get("disabled_issue_types", []) if str(item).strip()),
                "deprioritized_rule_ids": tuple(str(item) for item in value.get("deprioritized_rule_ids", []) if str(item).strip()),
                "deprioritized_issue_types": tuple(str(item) for item in value.get("deprioritized_issue_types", []) if str(item).strip()),
            }
            for key, value in payload.get("domain_profiles", {}).items()
            if isinstance(value, dict)
        },
    )


@lru_cache(maxsize=1)
def build_rule_registry() -> tuple[RuleRegistryEntry, ...]:
    profile = load_rule_priority_profile()
    entries: list[RuleRegistryEntry] = []
    for rule in ALL_RULES:
        family = _infer_rule_family(rule)
        entries.append(
            RuleRegistryEntry(
                rule_id=rule.rule_id,
                issue_type=rule.issue_type,
                rule_family=family,
                source_section=rule.source_section,
                merge_key=rule.merge_key or rule.issue_type,
                governance_tier=_infer_governance_tier(rule),
                rule_status=_infer_rule_status(rule),
                enabled_by_default=_infer_enabled_by_default(rule),
                default_priority=profile.default_family_priorities.get(family, 80),
                related_reference_ids=rule.related_reference_ids,
            )
        )
    return tuple(entries)


def rule_registry_map() -> dict[str, RuleRegistryEntry]:
    return {entry.rule_id: entry for entry in build_rule_registry()}


def _infer_rule_family(rule: RuleDefinition) -> str:
    if rule.rule_id.startswith("QUAL-"):
        return "qualification"
    if rule.rule_id.startswith("SCORE-"):
        return "scoring"
    if rule.rule_id.startswith("TECH-"):
        return "technical"
    if rule.rule_id.startswith("CONTRACT-"):
        return "commercial"
    return "general"


def _infer_governance_tier(rule: RuleDefinition) -> str:
    if rule.issue_type in {
        "excessive_supplier_qualification",
        "geographic_restriction",
        "one_sided_commercial_term",
        "payment_acceptance_linkage",
        "unclear_acceptance_standard",
    }:
        return "core"
    if rule.issue_type in {"qualification_domain_mismatch", "scoring_content_mismatch", "technical_justification_needed"}:
        return "scenario"
    return "support"


def _infer_rule_status(rule: RuleDefinition) -> str:
    tier = _infer_governance_tier(rule)
    if tier == "core":
        return "formal_active"
    if tier == "scenario":
        return "formal_catalog_sensitive"
    return "formal_support"


def _infer_enabled_by_default(rule: RuleDefinition) -> bool:
    return _infer_governance_tier(rule) in {"core", "scenario", "support"}
