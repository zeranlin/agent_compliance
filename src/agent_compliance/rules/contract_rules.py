from __future__ import annotations

import re

from agent_compliance.rules.base import RuleDefinition


RULES = [
    RuleDefinition(
        rule_id="CONTRACT-001",
        issue_type="one_sided_commercial_term",
        pattern=re.compile(r"财政审批的原因造成采购人延期付款|预付款未支付时，中标人仍必须在交货期内交货"),
        rationale="将付款和履约风险大面积转嫁给供应商，权利义务失衡。",
        severity_score=3,
        related_rule_ids=("RULE-008", "RULE-017", "RULE-003"),
        related_reference_ids=("CASESRC-009", "LEGAL-001"),
        source_section="商务要求",
        rewrite_hint="补充合理顺延和协商机制，避免当然免责和单方转嫁风险。",
    ),
    RuleDefinition(
        rule_id="CONTRACT-002",
        issue_type="unclear_acceptance_standard",
        pattern=re.compile(r"第三方质量检测部门|最新标准执行|采购人需要"),
        rationale="验收和第三方检测边界不清，可能引发履约争议。",
        severity_score=2,
        related_rule_ids=("RULE-003", "RULE-016"),
        related_reference_ids=("CASESRC-008", "LEGAL-001"),
        source_section="验收条件",
        rewrite_hint="明确验收清单、触发条件、检测范围和费用规则。",
    ),
    RuleDefinition(
        rule_id="CONTRACT-003",
        issue_type="other",
        pattern=re.compile(r"卫生清洁、保洁|垃圾的分类收集、清运|碳足迹盘查报告"),
        rationale="存在与项目主标的关系不清的义务或模板残留内容。",
        severity_score=2,
        related_rule_ids=("RULE-003",),
        related_reference_ids=("LEGAL-001",),
        source_section="商务要求",
        rewrite_hint="删除与主标的不直接相关的义务，或改成与安装履约直接相关的要求。",
    ),
]
