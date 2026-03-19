# 招标文件独立解析器设计

## 目标

在不破坏现有代码审查独立能力的前提下，新增一个可前置的独立原子能力：

- `tender_document_parser`

它的职责不是直接判断风险，而是先把招标文件按业务规则解析为结构化内容，再把真正需要重点审查的板块送入风险识别主链。

## 为什么要独立

当前主链已经补了：

- `tender_document_risk_scope_layer`
- `requirement_scope_layer`

但它们仍然是“在 review 主链内部给 clause 打标签”。

要进一步降低：

- 模板/提示污染
- 结构块误判
- 评分、技术、商务跨块串扰

需要一个更上游、可独立测试、可独立缓存、可单独开关的解析层。

## 独立能力定位

### `tender_document_parser` 负责

- 识别招标文件业务结构
- 识别风险作用域
- 识别条款功能与效力强度
- 生成结构化招标内容包

### `review pipeline` 负责

- 品目识别与场景理解
- 规则扫描
- analyzer
- 大模型关键节点
- 仲裁
- 法规语义
- 证据与导出

## 主链接入位置

```text
原始文件
-> normalize
-> (可选) tender_document_parser
-> review pipeline
```

对应当前实现：

```text
normalize
-> tender_document_parser
   -> tender_document_risk_scope_layer
   -> requirement_scope_layer
-> strategy / catalog / rules / analyzers / arbiter / evidence
```

## 第一版 schema

第一版先输出：

- `StructuredTenderDocument`
- `StructuredTenderSection`

### `StructuredTenderDocument`

- `source_path`
- `document_name`
- `parser_mode`
- `section_count`
- `sections`
- `core_section_count`
- `supporting_section_count`
- `out_of_scope_section_count`

### `StructuredTenderSection`

- `section_id`
- `document_structure_type`
- `risk_scope`
- `title`
- `clause_ids`
- `clause_count`
- `effective_clause_count`
- `high_weight_clause_count`
- `scope_reasons`

## parser_mode

第一版只支持三种模式：

- `off`
  - 不前置独立解析器
  - 保持原代码审查链路
- `assist`
  - 前置解析器
  - 解析结果优先供 review 使用
  - 原链路仍保底
- `required`
  - 必须先识别出核心风险板块
  - 否则中止进入审查主链

## 与现有两层的关系

### `tender_document_risk_scope_layer`

回答：

- 这段 clause 属于招标文件哪个业务结构块
- 处在什么风险作用域

### `requirement_scope_layer`

回答：

- 这段 clause 在其板块里起什么功能
- 条款效力强弱如何

### `tender_document_parser`

负责把这两层前置、收编成独立解析过程，并输出结构化结果。

## 第一版落地范围

第一版不要求完全替换旧链，只做：

1. 独立解析器模块落地
2. CLI / Web / review 主链支持 `parser_mode`
3. `assist` 模式下优先前置解析
4. `required` 模式下校验是否识别出核心风险板块

## 迁移策略

### 当前阶段

- review 仍可直接吃 `NormalizedDocument`
- parser 作为可选前置能力

### 下一阶段

- analyzer 逐步显式消费 parser 产出的结构化 sections
- 降低对“原始 clause 全文遍历”的依赖

## 收益

- 保持原代码审查功能独立可运行
- 给招标文件解析能力建立独立边界
- 方便逐文件 A/B 验证：
  - 不启用 parser
  - 启用 parser（assist）
- 后续可逐步把 risk_scope / clause_function / effect_strength 更深地下沉到 analyzer
