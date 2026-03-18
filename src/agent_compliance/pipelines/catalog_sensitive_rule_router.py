from __future__ import annotations

from dataclasses import dataclass

from agent_compliance.knowledge.procurement_catalog import CatalogClassification
from agent_compliance.knowledge.rule_registry import (
    RulePriorityProfile,
    RuleRegistryEntry,
    load_rule_priority_profile,
    rule_registry_map,
)
from agent_compliance.rules.base import RuleDefinition
from agent_compliance.rules.contract_rules import RULES as CONTRACT_RULES
from agent_compliance.rules.qualification_rules import RULES as QUALIFICATION_RULES
from agent_compliance.rules.scoring_rules import RULES as SCORING_RULES
from agent_compliance.rules.technical_rules import RULES as TECHNICAL_RULES


ALL_RULES = [*QUALIFICATION_RULES, *SCORING_RULES, *TECHNICAL_RULES, *CONTRACT_RULES]


@dataclass(frozen=True)
class RoutedRule:
    rule: RuleDefinition
    registry_entry: RuleRegistryEntry
    priority_score: int
    route_reason: str


def route_rules_for_catalog(
    classification: CatalogClassification | None,
    *,
    profile: RulePriorityProfile | None = None,
) -> list[RoutedRule]:
    profile = profile or load_rule_priority_profile()
    registry = rule_registry_map()
    domain_key = classification.primary_domain_key if classification else "general"
    domain_profile = profile.domain_profiles.get(domain_key, {})
    family_priorities = {**profile.default_family_priorities, **domain_profile.get("family_priorities", {})}
    issue_adjustments = {**profile.default_issue_type_adjustments, **domain_profile.get("issue_type_adjustments", {})}
    rule_adjustments = {**profile.default_rule_adjustments, **domain_profile.get("rule_adjustments", {})}

    routed: list[RoutedRule] = []
    for rule in ALL_RULES:
        entry = registry[rule.rule_id]
        score = family_priorities.get(entry.rule_family, entry.default_priority)
        score += issue_adjustments.get(rule.issue_type, 0)
        score += rule_adjustments.get(rule.rule_id, 0)
        routed.append(
            RoutedRule(
                rule=rule,
                registry_entry=entry,
                priority_score=score,
                route_reason=_route_reason(entry, domain_key, score, family_priorities, issue_adjustments, rule_adjustments),
            )
        )
    routed.sort(key=lambda item: (-item.priority_score, -item.rule.severity_score, item.rule.rule_id))
    return routed


def _route_reason(
    entry: RuleRegistryEntry,
    domain_key: str,
    score: int,
    family_priorities: dict[str, int],
    issue_adjustments: dict[str, int],
    rule_adjustments: dict[str, int],
) -> str:
    base = family_priorities.get(entry.rule_family, entry.default_priority)
    delta = score - base
    if delta > 0:
        return f"{domain_key} 场景对 {entry.rule_family} 家族和当前问题类型做了加权。"
    if entry.issue_type in issue_adjustments or entry.rule_id in rule_adjustments:
        return f"{domain_key} 场景对当前规则做了保守调度。"
    return f"按 {entry.rule_family} 家族默认优先级调度。"
