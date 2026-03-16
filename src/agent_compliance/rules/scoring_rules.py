from __future__ import annotations

import re

from agent_compliance.rules.base import RuleDefinition


RULES = [
    RuleDefinition(
        rule_id="SCORE-001",
        issue_type="duplicative_scoring_advantage",
        pattern=re.compile(r"营业执照或事业单位法人证书等证明资料扫描件，可得\d+分"),
        rationale="资格证明材料不宜再次转化为评分优势。",
        severity_score=3,
        related_rule_ids=("RULE-004", "RULE-012"),
        related_reference_ids=("CASESRC-004",),
        source_section="评标信息",
        rewrite_hint="删除资格证明材料加分，避免将资格审查内容重复转化为评分优势。",
    ),
    RuleDefinition(
        rule_id="SCORE-002",
        issue_type="irrelevant_certification_or_award",
        pattern=re.compile(r"全国科技型中小企业证明|守合同重信用企业|奖项|荣誉|信用等级"),
        rationale="与履约无明显关系的荣誉或企业属性不宜作为高分项。",
        severity_score=2,
        related_rule_ids=("RULE-010", "RULE-014", "RULE-004"),
        related_reference_ids=("CASESRC-001", "CASESRC-006"),
        source_section="评标信息",
        rewrite_hint="删除与履约无直接关系的荣誉、称号和信用等级加分项。",
    ),
    RuleDefinition(
        rule_id="SCORE-003",
        issue_type="ambiguous_requirement",
        pattern=re.compile(r"方案极合理|条理极清晰|综合比较|优、良、中、差"),
        rationale="主观评分分档表述较多，缺少量化锚点。",
        severity_score=2,
        related_rule_ids=("RULE-004", "RULE-011"),
        related_reference_ids=("CASESRC-003",),
        source_section="评标信息",
        rewrite_hint="把主观描述拆成分项分档和可核验指标，减少自由裁量空间。",
    ),
]
