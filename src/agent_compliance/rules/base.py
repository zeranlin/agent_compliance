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


RULE_SET_VERSION = "v0.1.0"
