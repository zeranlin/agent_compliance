# 引用资料元数据规范

## 目标

为本地法规依据库和案例口径库建立统一的轻量元数据结构，方便后续进行：
- 文档检索
- 自动引用
- 自动更新
- 规则与案例映射

## 适用范围

适用于以下目录中的引用资料文件：
- `docs/references/legal-authorities/`
- `docs/references/case-sources/`

## 推荐元字段

每份引用资料建议在标题下增加 `元数据` 小节，至少包含以下字段：

- `reference_id`：唯一编号
- `reference_type`：`legal_authority` 或 `case_source`
- `source_org`：来源机构
- `source_url`：原始官方链接
- `canonical_registry_url`：权威目录页链接（如适用）
- `doc_no`：发文字号或令号（如适用）
- `promulgation_date`：颁布日期（如适用）
- `validity_status`：有效、废止、失效、待核验等
- `authority_level`：法律、行政法规、财政部规章、规范性文件、政策解读等
- `verification_source`：最近一次有效性核验所依据的权威目录或原文来源
- `is_primary_source`：是否为原始权威来源
- `status`：有效、待核验、实务参考等
- `review_topics`：本资料主要支持的审查主题
- `related_rule_ids`：关联法规依据库编号
- `related_case_ids`：关联案例库编号
- `last_verified`：最近人工核验日期
- `last_registry_verified`：最近一次按权威目录核验日期（如适用）

## 示例

```md
## 元数据

- `reference_id`: `LEGAL-001`
- `reference_type`: `legal_authority`
- `source_org`: `财政部`
- `source_url`: `https://example.com`
- `canonical_registry_url`: `https://www.ccgp.gov.cn/zcfg/mofgz/`
- `doc_no`: `财政部令第87号`
- `promulgation_date`: `2017-07-11`
- `validity_status`: `有效`
- `authority_level`: `财政部规章`
- `verification_source`: `中国政府采购网-财政部规章`
- `is_primary_source`: `true`
- `status`: `有效`
- `review_topics`: `采购需求,评分标准,验收`
- `related_rule_ids`: `RULE-003`
- `related_case_ids`: `CASE-004, CASE-012`
- `last_verified`: `2026-03-14`
- `last_registry_verified`: `2026-03-18`
```

## 编号规则建议

### 法规依据类

- `LEGAL-001`
- `LEGAL-002`

### 案例口径类

- `CASESRC-001`
- `CASESRC-002`

## 使用约定

- `review_topics` 使用中文主题，多个值用逗号分隔。
- `related_rule_ids` 和 `related_case_ids` 使用现有样表编号。
- `last_verified` 使用 `YYYY-MM-DD`。
- `last_registry_verified` 使用 `YYYY-MM-DD`。
- 若尚未建立映射，可先填 `待补充`。
- `canonical_registry_url` 仅在存在权威目录页时填写；例如财政部规章可填写中国政府采购网“财政部规章”目录页。
- `verification_source` 用于说明有效性核验来源；如果没有目录页，应明确写“财政部官网原文”或其他权威原文来源。
- `authority_level` 应与资料位阶一致，避免把“办公厅通知”“规范性文件”误标为“财政部规章”。

## 最低落地要求

第一阶段至少做到：
- 每份引用资料都有 `reference_id`
- 每份引用资料都有 `source_url`
- 每份引用资料都有 `review_topics`
- 每份引用资料至少关联一个 `related_rule_ids`

这样已经足够支持后续半自动检索和引用。

第二阶段建议补充：
- 财政部规章类资料增加 `canonical_registry_url`
- 财政部规章类资料增加 `doc_no`、`promulgation_date`、`validity_status`
- 需要持续核验有效性的资料增加 `verification_source` 和 `last_registry_verified`
