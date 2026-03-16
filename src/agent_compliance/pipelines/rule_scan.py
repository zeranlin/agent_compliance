from __future__ import annotations

from itertools import chain

from agent_compliance.rules.base import RULE_SET_VERSION
from agent_compliance.rules.contract_rules import RULES as CONTRACT_RULES
from agent_compliance.rules.qualification_rules import RULES as QUALIFICATION_RULES
from agent_compliance.rules.scoring_rules import RULES as SCORING_RULES
from agent_compliance.rules.technical_rules import RULES as TECHNICAL_RULES
from agent_compliance.schemas import NormalizedDocument, RuleHit


ALL_RULES = list(chain(QUALIFICATION_RULES, SCORING_RULES, TECHNICAL_RULES, CONTRACT_RULES))


def run_rule_scan(document: NormalizedDocument) -> list[RuleHit]:
    hits: list[RuleHit] = []
    counter = 1
    for clause in document.clauses:
        for rule in ALL_RULES:
            if rule.pattern.search(clause.text):
                hits.append(
                    RuleHit(
                        rule_hit_id=f"RH-{counter:04d}",
                        rule_set_version=RULE_SET_VERSION,
                        issue_type_candidate=rule.issue_type,
                        matched_text=clause.text,
                        matched_clause_id=clause.clause_id,
                        line_start=clause.line_start,
                        line_end=clause.line_end,
                        rationale=rule.rationale,
                        severity_score=rule.severity_score,
                    )
                )
                counter += 1
    return hits
