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
        related_rule_ids=("RULE-002", "RULE-003"),
        related_reference_ids=("LEGAL-001", "CASESRC-005"),
        source_section="申请人的资格要求",
        rewrite_hint="删除企业性质限制，改回法定主体资格和履约必需能力要求。",
    ),
    RuleDefinition(
        rule_id="QUAL-002",
        issue_type="excessive_supplier_qualification",
        pattern=re.compile(r"注册资本不低于|年收入不低于|净利润不低于|经营年限不低于"),
        rationale="设置与项目履约弱相关的一般性财务或经营年限门槛。",
        severity_score=3,
        related_rule_ids=("RULE-003", "RULE-015"),
        related_reference_ids=("LEGAL-001", "CASESRC-007", "CASESRC-002"),
        source_section="申请人的资格要求",
        rewrite_hint="删除一般性财务和经营年限门槛，改用法定资质和履约能力证明。",
    ),
    RuleDefinition(
        rule_id="QUAL-003",
        issue_type="irrelevant_certification_or_award",
        pattern=re.compile(r"国家级高新技术企业|守合同重信用企业|AAA"),
        rationale="将企业称号、荣誉或信用等级作为门槛或高权重因素，可能与履约无直接关系。",
        severity_score=3,
        related_rule_ids=("RULE-003", "RULE-010", "RULE-014"),
        related_reference_ids=("LEGAL-001", "CASESRC-001", "CASESRC-006"),
        source_section="申请人的资格要求",
        rewrite_hint="删除企业称号或荣誉门槛，改为与标的直接相关的履约能力条件。",
    ),
]
