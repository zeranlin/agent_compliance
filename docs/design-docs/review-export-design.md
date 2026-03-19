# 审查结果导出功能方案

## 目标

为代码审查结果提供稳定、统一、可复用的导出能力，满足以下场景：

- 人工复核
- 业务/采购/法务协同改稿
- 对外汇报与留痕
- 系统对接与二次加工
- benchmark 与复盘材料归档

设计原则：
- 先统一字段，再实现导出
- 先做高价值格式，再扩展复杂版式
- 先支持主问题版和完整明细版，再考虑更多模板
- 导出结构尽量复用现有 `Finding`、法规语义层、品目层和证据层结果，避免再拼一套旁路数据

## 适用范围

本方案适用于：
- CLI `review`
- Web `/review-next`
- 后续规则管理页、benchmark 页面上的结果复用

当前导出默认服务场景：
- 采购需求形成与发布前审查
- 采购人改稿
- 发布前复核与留痕

本方案暂不优先覆盖：
- 精美 Word/PDF 自动排版报告
- 多模板自由编排
- 富格式审批流文档

## 导出格式

第一阶段优先支持 3 类格式：

### 1. Markdown

适合：
- 仓库留痕
- 人工复核
- 审查结论归档
- 继续编辑加工

输出特点：
- 可读性强
- 便于 Git diff
- 与现有 `docs/generated/reviews/*.md` 兼容

### 2. Excel

适合：
- 业务方、采购方、法务方协同改稿
- 一行一条问题的表格化处理
- 线下流转

输出特点：
- 字段固定
- 可筛选、排序、批注
- 更适合“整改跟踪”

建议文件扩展名：
- `.xlsx`

### 3. JSON

适合：
- 系统集成
- 二次分析
- benchmark
- 差异对比与自动化流程

输出特点：
- 结构稳定
- 机器可读
- 与现有 `review.to_dict()` 对齐

## 导出模式

第一阶段统一支持两种模式：

### 1. 主问题版

用途：
- 快速汇报
- 高层复核
- 先看章节级主风险

特点：
- 仅导出章节级主问题或仲裁后保留的高价值问题
- 每个问题附代表性证据
- 问题数量更少，更接近人工正式审查意见

### 2. 完整明细版

用途：
- 详细改稿
- 全量追踪
- benchmark/调试

特点：
- 导出全部保留 findings
- 保留所有字段与定位信息

## 导出对象结构

建议统一使用以下导出层级：

```json
{
  "document": {},
  "review_summary": {},
  "export_meta": {},
  "findings": []
}
```

### `document`

包含：
- `document_name`
- `source_path` 或 `source_name`
- `review_scope`
- `jurisdiction`

### `review_summary`

包含：
- `overall_risk_summary`
- `finding_count`
- `high_risk_count`
- `medium_risk_count`
- `low_risk_count`
- `primary_catalog_name`
- `primary_domain_key`
- `is_mixed_scope`
- `procurement_stage_name`
- `procurement_stage_goal`

### `export_meta`

包含：
- `export_format`
- `export_mode`
- `export_timestamp`
- `generated_by`
- `review_result_version`
- `export_intent`

### `findings`

每条 finding 导出时复用现有 schema，并补充必要展示字段。

## 主问题版字段定义

主问题版建议字段：

- `finding_id`
- `problem_title`
- `chapter_group`
- `risk_level`
- `confidence`
- `compliance_judgment`
- `source_section`
- `section_path`
- `table_or_item_label`
- `page_hint`
- `text_line_start`
- `text_line_end`
- `representative_evidence`
- `why_it_is_risky`
- `legal_or_policy_basis`
- `primary_authority`
- `secondary_authorities`
- `applicability_logic`
- `rewrite_suggestion`
- `needs_human_review`
- `human_review_reason`
- `issue_type`
- `primary_catalog_name`
- `primary_domain_key`
- `is_mixed_scope`

说明：
- `representative_evidence` 使用证据层输出，不直接等于 `source_text`
- `chapter_group` 统一归为：
  - `资格`
  - `评分`
  - `技术`
  - `商务/验收`

## 完整明细版字段定义

完整明细版建议字段：

- `finding_id`
- `document_name`
- `problem_title`
- `issue_type`
- `risk_level`
- `severity_score`
- `confidence`
- `compliance_judgment`
- `source_section`
- `section_path`
- `clause_id`
- `table_or_item_label`
- `page_hint`
- `text_line_start`
- `text_line_end`
- `source_text`
- `why_it_is_risky`
- `impact_on_competition_or_performance`
- `legal_or_policy_basis`
- `primary_authority`
- `secondary_authorities`
- `applicability_logic`
- `rewrite_suggestion`
- `needs_human_review`
- `human_review_reason`
- `primary_catalog_name`
- `secondary_catalog_names`
- `primary_domain_key`
- `is_mixed_scope`
- `source_type`
  - 规则命中 / 结构分析 / 全文辅助扫描 / 仲裁保留

## Excel 字段建议

Excel 第一版建议固定为以下列顺序：

1. 问题标题
2. 章节
3. 风险等级
4. 置信度
5. 合规判断
6. 位置
7. 页码提示
8. 原文摘录
9. 风险说明
10. 法规依据
11. 主依据
12. 辅依据
13. 适用逻辑
14. 修改建议
15. 是否需复核
16. 复核原因
17. 问题类型
18. 主品目
19. 审查领域
20. 混合采购

说明：
- `位置` 推荐由 `section_path + clause_id + table_or_item_label` 组合
- 主问题版 Excel 使用 `representative_evidence`
- 明细版 Excel 使用 `source_text`

## Markdown 导出结构建议

### 主问题版

```md
# 审查结果

## 文件信息
...

## 风险摘要
...

## 主问题
### F-001 问题标题
- 章节：
- 风险等级：
- 代表性证据：
- 风险说明：
- 法规依据：
- 适用逻辑：
- 修改建议：
```

### 完整明细版

按现有 `docs/generated/reviews/*.md` 结构为主，只补：
- 主依据
- 辅依据
- 适用逻辑
- 主品目/审查领域

## Web 页面入口

导出入口统一放在 `review-next` 顶部结果摘要区。

建议交互：
- `导出` 按钮
- 下拉选择：
  - `导出 Markdown（主问题版）`
  - `导出 Markdown（完整明细版）`
  - `导出 Excel（主问题版）`
  - `导出 Excel（完整明细版）`
  - `导出 JSON（主问题版）`
  - `导出 JSON（完整明细版）`

前端展示原则：
- 不增加新页面
- 不改变当前审查主流程
- 仅在结果已生成后显示导出入口

## 后端接口建议

建议新增接口：

### `POST /api/export-review`

请求体：

```json
{
  "review": { "...": "review result dict" },
  "document": { "...": "document payload" },
  "format": "markdown | xlsx | json",
  "mode": "summary | full"
}
```

返回：
- 文件下载流
或
- 本地导出文件路径 + 下载 URL

### 也可选的实现

如果复用现有本地文件写入模式，也可以：
- 先写到 `docs/generated/exports/`
- 再返回：

```json
{
  "path": "...",
  "filename": "...",
  "format": "...",
  "mode": "..."
}
```

## 建议目录结构

```text
docs/generated/exports/
  2026-03-18/
    <filehash>-summary.md
    <filehash>-summary.xlsx
    <filehash>-summary.json
    <filehash>-full.md
    <filehash>-full.xlsx
    <filehash>-full.json
```

说明：
- 与 `reviews/` 分开，避免混淆“审查标准产物”和“面向交付的导出产物”

## 复用原则

导出功能必须尽量复用现有层，不应重新发明字段：

- 定位字段：复用 `Finding`
- 法规字段：复用 `legal_authority_reasoner`
- 证据字段：复用 `review_evidence`
- 品目字段：复用 `procurement_catalog_classifier`
- 置信度字段：复用 `confidence_calibrator`

## 实现优先级

### P0

- JSON 导出
- Markdown 导出
- 主问题版 / 完整明细版两种模式
- `review-next` 导出入口

### P1

- Excel 导出
- 导出文件写入 `docs/generated/exports/`
- 导出测试

### P2

- 自定义导出模板
- Word/PDF 报告
- 按章节导出
- 规则管理页和 benchmark 页复用导出能力

## 验证标准

导出功能第一阶段至少满足：

- 同一份结果可稳定导出为 Markdown / JSON
- 主问题版与完整明细版字段差异清晰
- Web 端能点击导出
- 导出内容保留：
  - 风险标题
  - 定位信息
  - 证据
  - 法规依据
  - 适用逻辑
  - 修改建议
  - 品目信息

## 一句话结论

结果导出功能应作为 `review-next` 的配套能力建设，不再单开新页面。第一阶段优先做 `Markdown + JSON + Excel` 三种格式，并统一支持“主问题版 / 完整明细版”两种模式，以满足人工复核、业务改稿、系统对接和留痕归档四类核心场景。
