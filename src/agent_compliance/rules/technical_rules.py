from __future__ import annotations

import re

from agent_compliance.rules.base import RuleDefinition


RULES = [
    RuleDefinition(
        rule_id="TECH-001",
        issue_type="narrow_technical_parameter",
        pattern=re.compile(r"无线插拔技术|无需防水盖|12MHz、20MHz|兼容高清电子胃肠镜"),
        rationale="技术路线或参数组合较细，存在指向少数产品体系的风险。",
        severity_score=2,
    ),
]
