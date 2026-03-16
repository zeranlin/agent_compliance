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
        related_rule_ids=("RULE-003",),
        related_reference_ids=("LEGAL-001", "CASESRC-001"),
        source_section="技术要求",
        rewrite_hint="改为功能效果导向的兼容性或性能要求，并补充必要性说明。",
        merge_key="technical-parameter-narrow",
    ),
    RuleDefinition(
        rule_id="TECH-002",
        issue_type="narrow_technical_parameter",
        pattern=re.compile(r"指定品牌|指定型号|专有平台|专有接口|仅兼容.*现有系统|兼容.*原有设备"),
        rationale="兼容性、平台或接口要求写法较窄，存在锁定既有品牌或技术体系的风险。",
        severity_score=2,
        related_rule_ids=("RULE-003",),
        related_reference_ids=("LEGAL-001", "CASESRC-001"),
        source_section="技术要求",
        rewrite_hint="将品牌、平台或既有系统要求改为功能兼容和效果要求，并补充必要性说明。",
        merge_key="technical-compatibility",
    ),
    RuleDefinition(
        rule_id="TECH-003",
        issue_type="technical_justification_needed",
        pattern=re.compile(r"202\d年.*投标截止日前.*(CMA|CNAS)|第三方.*(CMA|CNAS).*(阻燃|抗菌|抗病毒|防霉|盐雾|致癌染料|有机锡|邻苯|含氯苯酚)"),
        rationale="检测报告时段、机构资质与多项性能指标叠加设置，可能具有场景合理性，但通常需要采购人进一步说明必要性。",
        severity_score=2,
        related_rule_ids=("RULE-003", "RULE-016"),
        related_reference_ids=("LEGAL-001", "CASESRC-001"),
        source_section="技术要求",
        rewrite_hint="补充市场调研、场景必要性和检测要求设置依据，能以国家或行业标准表述的尽量不叠加细化证明形式。",
        merge_key="technical-justification",
    ),
    RuleDefinition(
        rule_id="TECH-004",
        issue_type="technical_justification_needed",
        pattern=re.compile(r"阻燃|抗菌|抗病毒|防霉|环保|盐雾|致癌染料|有机锡|邻苯|含氯苯酚"),
        rationale="技术指标涉及安全、环保或院感控制等场景要求时，可能合理，但需要结合采购场景和市场供给说明必要性。",
        severity_score=2,
        related_rule_ids=("RULE-003", "RULE-016"),
        related_reference_ids=("LEGAL-001", "CASESRC-001"),
        source_section="技术要求",
        rewrite_hint="如确需保留安全、环保或院感控制指标，应补充适用场景、标准依据和市场调研说明。",
        merge_key="technical-justification",
    ),
]
