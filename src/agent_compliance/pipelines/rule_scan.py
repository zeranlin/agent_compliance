from __future__ import annotations

from itertools import chain

from agent_compliance.knowledge.procurement_catalog import CatalogClassification, classify_procurement_catalog
from agent_compliance.pipelines.catalog_sensitive_rule_router import route_rules_for_catalog
from agent_compliance.rules.base import RULE_SET_VERSION
from agent_compliance.rules.contract_rules import RULES as CONTRACT_RULES
from agent_compliance.rules.qualification_rules import RULES as QUALIFICATION_RULES
from agent_compliance.rules.scoring_rules import RULES as SCORING_RULES
from agent_compliance.rules.technical_rules import RULES as TECHNICAL_RULES
from agent_compliance.schemas import NormalizedDocument, RuleHit


ALL_RULES = list(chain(QUALIFICATION_RULES, SCORING_RULES, TECHNICAL_RULES, CONTRACT_RULES))


def run_rule_scan(
    document: NormalizedDocument,
    classification: CatalogClassification | None = None,
) -> list[RuleHit]:
    classification = classification or classify_procurement_catalog(document)
    routed_rules = route_rules_for_catalog(classification)
    hits: list[RuleHit] = []
    counter = 1
    for clause in document.clauses:
        matched_by_merge_key: dict[str, RuleHit] = {}
        for routed_rule in routed_rules:
            rule = routed_rule.rule
            if rule.pattern.search(clause.text):
                hit = RuleHit(
                    rule_hit_id=f"RH-{counter:04d}",
                    rule_id=rule.rule_id,
                    merge_key=rule.merge_key or rule.issue_type,
                    rule_set_version=RULE_SET_VERSION,
                    issue_type_candidate=rule.issue_type,
                    matched_text=clause.text,
                    matched_clause_id=clause.clause_id,
                    line_start=clause.line_start,
                    line_end=clause.line_end,
                    rationale=rule.rationale,
                    severity_score=rule.severity_score,
                    related_rule_ids=rule.related_rule_ids,
                    related_reference_ids=rule.related_reference_ids,
                    source_section=rule.source_section,
                    rewrite_hint=rule.rewrite_hint,
                )
                merge_key = hit.merge_key
                if merge_key not in matched_by_merge_key:
                    matched_by_merge_key[merge_key] = hit
                    counter += 1
        hits.extend(matched_by_merge_key.values())
    return hits
