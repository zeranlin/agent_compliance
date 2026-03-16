from __future__ import annotations

import re

from agent_compliance.rules.base import RuleDefinition


RULES = [
    RuleDefinition(
        rule_id="QUAL-001",
        issue_type="excessive_supplier_qualification",
        pattern=re.compile(r"外商投资及民营企业|国资企业不具备投标资格"),
        rationale="按企业性质限制供应商范围，可能构成差别待遇。",
        severity_score=3,
    ),
    RuleDefinition(
        rule_id="QUAL-002",
        issue_type="excessive_supplier_qualification",
        pattern=re.compile(r"注册资本不低于|年收入不低于|净利润不低于|经营年限不低于"),
        rationale="设置与项目履约弱相关的一般性财务或经营年限门槛。",
        severity_score=3,
    ),
    RuleDefinition(
        rule_id="QUAL-003",
        issue_type="irrelevant_certification_or_award",
        pattern=re.compile(r"国家级高新技术企业|守合同重信用企业|AAA"),
        rationale="将企业称号、荣誉或信用等级作为门槛或高权重因素，可能与履约无直接关系。",
        severity_score=3,
    ),
]
