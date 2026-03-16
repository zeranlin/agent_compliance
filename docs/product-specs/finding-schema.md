# Finding Schema

## 目的

本 schema 定义了每条合规发现的最小结构化输出，以便结果能够：
- 被人工复核
- 在不同模型运行之间对比
- 被纳入评测打分
- 转换为下游报告产物

## 审查结果外层结构

每次文档审查都应产出一个结果对象。

```json
{
  "document_name": "string",
  "review_scope": "string",
  "jurisdiction": "string or null",
  "review_timestamp": "ISO-8601 string",
  "overall_risk_summary": "string",
  "findings": [],
  "items_for_human_review": [],
  "review_limitations": []
}
```

## Finding 对象

`findings` 数组中的每个对象都应遵循以下结构。

```json
{
  "finding_id": "string",
  "document_name": "string",
  "problem_title": "string",
  "page_hint": "string or null",
  "clause_id": "string",
  "source_section": "string",
  "section_path": "string or null",
  "table_or_item_label": "string or null",
  "text_line_start": 0,
  "text_line_end": 0,
  "source_text": "string",
  "issue_type": "string",
  "risk_level": "high | medium | low | none",
  "severity_score": 0,
  "confidence": "high | medium | low",
  "compliance_judgment": "likely_non_compliant | potentially_problematic | likely_compliant | needs_human_review",
  "why_it_is_risky": "string",
  "impact_on_competition_or_performance": "string",
  "legal_or_policy_basis": "string or null",
  "rewrite_suggestion": "string",
  "needs_human_review": true,
  "human_review_reason": "string or null"
}
```

## 字段说明

### `finding_id`

在同一次审查结果中使用稳定编号，如 `F-001`。

### `document_name`

填写来源文件名或来源文档标识，方便在多文件场景下快速回溯。

### `problem_title`

用于输出更适合人工复核和正式审查意见展示的问题标题，例如：
- `评分中设置与履约弱相关的荣誉资质加分`
- `技术参数组合存在定向或过窄风险`

### `page_hint`

用于记录页码或页码区间，如 `第28页`、`第28-29页`。  
对于 Word、PDF、扫描件等文档，页码通常比纯行号更适合人工快速定位。

### `clause_id`

优先使用原文编号，如 `3.2`、`表4/第2行`、`评分项A`。

### `source_section`

使用最近的、有意义的章节标签，例如 `技术参数`、`资格要求`、`评分标准`。

### `section_path`

用于记录完整章节路径，如 `七、采购实施计划-5.3 分值-项目负责人业绩`。  
这是人工审查时最重要的主定位字段之一。

### `table_or_item_label`

用于记录表格名、评分项名、采购标的项名等，如 `评分表-第2项-服务团队`。  
当问题位于表格、清单或评分项中时，应优先补充该字段。

### `text_line_start` / `text_line_end`

用于记录文本抽取后的起止行号。  
这两个字段属于辅助定位字段，适用于纯文本副本、Markdown、稳定抽取文本等场景。  
若当前文档无法稳定提供行号，可填 `0` 或在后续实现中留空。

### `source_text`

复制原始条款全文，或复制满足可追溯要求的最小必要片段。

### `issue_type`

除非后续规格扩展该列表，否则使用以下标准化问题类型之一：
- `brand_or_model_designation`
- `narrow_technical_parameter`
- `excessive_supplier_qualification`
- `geographic_restriction`
- `irrelevant_certification_or_award`
- `duplicative_scoring_advantage`
- `unclear_acceptance_standard`
- `one_sided_commercial_term`
- `ambiguous_requirement`
- `other`

### `risk_level`

使用规则如下：
- `high`：条款很可能造成排他性竞争限制或实质性不公平
- `medium`：存在较强合规疑点，但也可能有一定业务正当性
- `low`：表述建议优化，但风险相对有限
- `none`：条款大概率可接受，仅在无问题评测样例中保留

### `severity_score`

使用 `0` 到 `3` 的整数，便于评测打分：
- `0`：无明显问题
- `1`：存在起草瑕疵或轻微风险
- `2`：存在实质性合规疑点
- `3`：很可能属于严重不合规或具有明确排他效果

### `confidence`

使用规则如下：
- `high`：仅凭当前条款即可较稳定支持结论
- `medium`：结论较合理，但依赖一定上下文
- `low`：片段不完整、表述模糊，或高度依赖法域背景

### `compliance_judgment`

使用以下值：
- `likely_non_compliant`
- `potentially_problematic`
- `likely_compliant`
- `needs_human_review`

### `why_it_is_risky`

用直白语言解释风险逻辑，重点说明其与竞争、公平、履约相关性、可衡量性的关系。

### `impact_on_competition_or_performance`

解释实际影响，例如压缩合格供应商范围、将需求写死为单一产品、或使验收无法验证。

### `legal_or_policy_basis`

仅在目标法域内依据明确且可支持时填写；否则使用 `null`，并在必要时升级人工复核。

### `rewrite_suggestion`

提供更合规或更低风险的替代表述。优先使用功能导向、性能导向语言，而不是指向特定供应商的语言。

### `needs_human_review`

只有当采购或法务人员确实需要对该 finding 进行明确复核时，才设置为 `true`。

### `human_review_reason`

当 `needs_human_review = true` 时必须填写。示例：
- `地方性规则可能在特定场景下允许该条款`
- `兼容性需求可能使较窄参数具有合理性`
- `文档片段不完整`

## 严重度模型

应在各类样例中统一使用以下模型。

### Severity 3

典型触发情形：
- 直接指定品牌或型号，且没有等效路径
- 设置与履约无关的供应商属地限制
- 强制要求与履约无直接关系的奖项、排名或专有授权
- 经验或人员门槛明显定制化，排除大多数竞争者

### Severity 2

典型触发情形：
- 技术参数明显偏窄、存在定向嫌疑
- 评分项重复资格门槛，或奖励无关认证
- 验收条款实质性模糊、难以验证

### Severity 1

典型触发情形：
- 表述存在歧义
- 验收指标不完整
- 服务条款需要澄清，但尚不构成明显排他

### Severity 0

典型触发情形：
- 中性的性能要求
- 合理的等效表述
- 客观、可量化、与履约相关的评分或验收标准

## 置信度模型

### High confidence

当条款本身已能强烈支持该 finding，且不依赖额外上下文时使用。

### Medium confidence

当 finding 具有较强依据，但仍可能存在合理业务解释时使用。

### Low confidence

当文本片段过少、法域差异影响较大，或特殊采购场景可能改变结论时使用。

## 输出规则

- 对存在风险的 finding，不应省略 `rewrite_suggestion`，除非智能体明确说明为何无法安全改写。
- 不要把法律条文当作装饰性引用。
- 如果一个条款包含多个应分别整改的风险，不要把它们粗暴合并为单个 finding。
- 对大概率合规的条款，通常可不出现在常规审查输出中；若用于评测或报告，可保留并将 `severity_score` 设为 `0`。
- 每条高风险或中风险 finding 都应至少具备 `document_name`、`source_section`、`clause_id`、`source_text` 四项定位信息。
- 对长文档、表格型文件和评分标准类文件，应优先补充 `page_hint`、`section_path`、`table_or_item_label`。
