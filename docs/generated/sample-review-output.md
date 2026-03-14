# 样例审查输出

## 场景

这是一个针对简短采购需求片段的演示性输出。

## 输入片段

```text
1. 投标产品必须为A品牌X2000型号服务器，不接受其他品牌替代。
2. 供应商须在采购人所在地行政区域内设有分公司，否则投标无效。
3. 项目建成后应达到先进水平，并保证采购人满意后组织验收。
```

## 结构化结果示例

```json
{
  "document_name": "sample-procurement-needs.md",
  "review_scope": "技术要求与商务条款",
  "jurisdiction": null,
  "review_timestamp": "2026-03-14T00:00:00Z",
  "overall_risk_summary": "该片段包含多项可能不当限制竞争或造成验收标准不可验证的条款。",
  "findings": [
    {
      "finding_id": "F-001",
      "clause_id": "1",
      "source_section": "技术要求",
      "source_text": "投标产品必须为A品牌X2000型号服务器，不接受其他品牌替代。",
      "issue_type": "brand_or_model_designation",
      "risk_level": "high",
      "severity_score": 3,
      "confidence": "high",
      "compliance_judgment": "likely_non_compliant",
      "why_it_is_risky": "该条款直接指定品牌和型号，并排除替代方案，在未说明必要性能依据的情况下会实质性压缩竞争范围。",
      "impact_on_competition_or_performance": "该表述可能排除具备等效功能和性能的产品参与竞争。",
      "legal_or_policy_basis": null,
      "rewrite_suggestion": "将品牌型号表述改为满足项目业务需求的功能和性能指标，并允许满足等效技术要求的产品参与竞争。",
      "needs_human_review": false,
      "human_review_reason": null
    },
    {
      "finding_id": "F-002",
      "clause_id": "2",
      "source_section": "资格要求",
      "source_text": "供应商须在采购人所在地行政区域内设有分公司，否则投标无效。",
      "issue_type": "geographic_restriction",
      "risk_level": "high",
      "severity_score": 3,
      "confidence": "high",
      "compliance_judgment": "likely_non_compliant",
      "why_it_is_risky": "该条款将本地设立分公司设为刚性资格门槛，但没有说明为什么履约必须依赖采购人所在地的分支机构。",
      "impact_on_competition_or_performance": "它可能排除异地但具备完整履约能力的供应商，从而削弱公平竞争。",
      "legal_or_policy_basis": null,
      "rewrite_suggestion": "将属地机构要求改为中标后在约定时限内提供本地化服务能力或驻场响应机制，并允许通过服务承诺或合作服务网点证明履约能力。",
      "needs_human_review": false,
      "human_review_reason": null
    },
    {
      "finding_id": "F-003",
      "clause_id": "3",
      "source_section": "验收要求",
      "source_text": "项目建成后应达到先进水平，并保证采购人满意后组织验收。",
      "issue_type": "unclear_acceptance_standard",
      "risk_level": "medium",
      "severity_score": 2,
      "confidence": "high",
      "compliance_judgment": "potentially_problematic",
      "why_it_is_risky": "该验收表述依赖“先进水平”“采购人满意”等主观概念，而不是客观、可测试的标准。",
      "impact_on_competition_or_performance": "主观验收条件会提高履约争议风险，因为供应商无法预先验证何为合格交付。",
      "legal_or_policy_basis": null,
      "rewrite_suggestion": "将验收要求改为依据明确的功能、性能、测试方法和验收标准进行验收，避免使用'先进水平'或'采购人满意'等主观表述。",
      "needs_human_review": false,
      "human_review_reason": null
    }
  ],
  "items_for_human_review": [],
  "review_limitations": [
    "当前未提供特定法域的法规依据集合。"
  ]
}
```
