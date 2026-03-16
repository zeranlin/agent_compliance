from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    issue_type: str
    pattern: re.Pattern[str]
    rationale: str
    severity_score: int
    related_rule_ids: tuple[str, ...]
    related_reference_ids: tuple[str, ...]
    source_section: str
    rewrite_hint: str
    merge_key: str | None = None


RULE_SET_VERSION = "v0.2.0"
