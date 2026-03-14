# 风险定位字段规范

## 目标

为政府采购需求合规审查建立统一的“风险定位能力”，确保每条问题都能被快速回溯到原始文件中的具体位置，方便人工核对和修改。

## 为什么不能只依赖行号

在政府采购场景中，原始文件通常是 Word、PDF、扫描件或表格型文档。  
这类文件在导出为文本后，行号往往不稳定，因此主定位方式不应只依赖行号。

更实用的做法是采用“主定位 + 辅助定位”的组合。

## 主定位字段

### 1. `document_name`

用于区分来源文件。

示例：
- `采购需求（会计） - 修订稿8.28(1)(1).doc`

### 2. `page_hint`

用于快速翻页定位。

示例：
- `第28页`
- `第28-29页`

### 3. `section_path`

用于记录完整章节路径，是最适合人工快速查找的字段。

示例：
- `七、采购实施计划-3.供应商资格条件-3.3`
- `5.3 分值-项目负责人业绩`

### 4. `clause_id`

用于记录条款编号、评分项编号、表格行编号。

示例：
- `3.3`
- `评分项4`
- `表2/第3行`

### 5. `table_or_item_label`

当问题位于表格、评分项、采购清单、合同条款列表时，用于补充更友好的标签。

示例：
- `评分表-服务团队`
- `采购标的汇总表-第3行`

### 6. `source_text`

复制最小必要原文，是所有定位信息中的最终核对依据。

## 辅助定位字段

### 1. `text_line_start`
### 2. `text_line_end`

适用场景：
- 已提取成稳定文本副本
- Markdown
- 纯文本政策文件

不适用场景：
- 原始 Word 排版频繁变化
- PDF 提取后换行不稳定
- 表格内容复杂

## 推荐定位优先级

在正式审查输出中，建议优先使用以下顺序：

1. `section_path`
2. `clause_id`
3. `page_hint`
4. `table_or_item_label`
5. `source_text`
6. `text_line_start/text_line_end`

## 推荐展示格式

```text
位置：七、采购实施计划-5.3 分值-项目负责人业绩
页码：第28页
编号：评分项2
原文：拟担任项目负责人需为投标人公司主要负责人（高管）……
```

## 适用建议

### Word/PDF 文件

优先使用：
- `document_name`
- `page_hint`
- `section_path`
- `clause_id`
- `source_text`

### 表格型评分标准

优先使用：
- `section_path`
- `table_or_item_label`
- `clause_id`
- `source_text`

### 文本副本或脚本处理中间件

可补充：
- `text_line_start`
- `text_line_end`

## 最低要求

每条中高风险 finding 至少应提供：
- `document_name`
- `section_path` 或 `source_section`
- `clause_id`
- `source_text`

对长文档和正式审查意见，建议同时提供：
- `page_hint`

对评分表、参数表、清单类文件，建议同时提供：
- `table_or_item_label`
