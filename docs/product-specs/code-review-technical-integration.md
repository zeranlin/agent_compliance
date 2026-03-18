# 代码审查能力技术对接说明

## 1. 文档目标

本文档面向需要接入本项目代码审查能力的技术团队，说明：
- 本地运行方式
- CLI 与 Web 入口
- 输入输出格式
- 集成建议
- 规则候选与 benchmark gate 的对接边界

## 2. 集成方式概览

当前建议的接入方式有两类：

### 2.1 本地 CLI 接入

适合：
- 批处理
- 本地任务编排
- 脚本式集成

入口命令：

```bash
PYTHONPATH=src python3 -m agent_compliance normalize <file>
PYTHONPATH=src python3 -m agent_compliance scan-rules <file> --json
PYTHONPATH=src python3 -m agent_compliance review <file> --json
PYTHONPATH=src python3 -m agent_compliance review <file> --json --use-llm
PYTHONPATH=src python3 -m agent_compliance eval --json
```

### 2.2 本地 Web 接入

适合：
- 审查工作台
- 人机协同复核
- 演示与内部试运行

启动命令：

```bash
PYTHONPATH=src python3 -m agent_compliance web
```

默认地址：
- `http://127.0.0.1:8765`

## 3. 当前接口

### 3.1 `POST /api/review`

用途：
- 上传文件并执行完整审查链路

请求方式：
- `multipart/form-data`

字段：
- `file`
- `use_llm`
- `use_cache`

返回结构核心字段：
- `cache`
- `llm`
- `document`
- `review`
- `llm_review`
- `outputs`

### 3.2 `POST /api/open-source`

用途：
- 在本机打开原始文件

### 3.3 `GET /api/rules`

用途：
- 获取规则管理页面数据

### 3.4 `POST /api/rules/decision`

用途：
- 对候选规则执行：
  - 确认入库
  - 暂缓
  - 忽略

## 4. 关键输入对象

### 4.1 标准化文档

`NormalizedDocument` 关键字段：
- `source_path`
- `document_name`
- `file_hash`
- `normalized_text_path`
- `clause_count`
- `clauses`
- `page_map`

### 4.2 finding

`Finding` 关键字段：
- `finding_id`
- `problem_title`
- `page_hint`
- `clause_id`
- `source_section`
- `section_path`
- `table_or_item_label`
- `text_line_start`
- `text_line_end`
- `source_text`
- `issue_type`
- `risk_level`
- `confidence`
- `compliance_judgment`
- `why_it_is_risky`
- `legal_or_policy_basis`
- `rewrite_suggestion`
- `finding_origin`

### 4.3 review result

`ReviewResult` 关键字段：
- `document_name`
- `review_scope`
- `review_timestamp`
- `overall_risk_summary`
- `findings`
- `items_for_human_review`
- `review_limitations`

## 5. 当前处理链路

标准链路：

1. `run_normalize(file)`
2. `run_rule_scan(normalized)`
3. `build_review_result(normalized, hits)`
4. `enhance_review_result(review, llm_config)`
5. `apply_llm_review_tasks(normalized, review, llm_config, output_stem=...)`
6. `write_review_outputs(review, output_stem)`

说明：
- 如启用缓存，会在 `review` 之前尝试命中缓存
- 如启用 LLM，会进入模型辅助审查
- 最终统一输出 Markdown 和 JSON

## 6. 本地模型接入方式

当前本地模型通过兼容 OpenAI 风格接口接入。

配置来源：
- `detect_llm_config()`
- 本地 `.env.local`

当前能力：
- 可显式启用或关闭
- 支持自动探测 `/v1/models`
- 当默认模型不可用时可回退到可用模型

当前模型任务：
- 模板错贴与标的域不匹配
- 评分结构判断
- 商务链路联合判断
- 全文辅助扫描

原则：
- 模型作为辅助审查层
- 不直接替代最终裁判
- 新增问题必须经过仲裁层

## 7. 缓存与一致性

当前 review 缓存键由以下要素组成：
- `file_hash`
- `rule_set_version`
- `reference_snapshot`
- `review_pipeline_version`

缓存能力：
- 可显式开启
- 支持 `--refresh-cache`
- 结果中返回缓存状态

一致性策略：
- 尽量复用标准化输入、规则命中和 findings
- 避免对同一文件反复整篇自由推理

## 8. 离线法规资料层

当前代码审查离线引用的主要资料是：
- `docs/references/legal-authorities/*.md`

这意味着当前已经支持：
- 基于本地法规摘要和元数据进行离线引用

当前尚未支持：
- 从本地权威原文快照中直接检索条文
- 从本地标准化法规文本中做更细粒度摘录

后续建议新增：
- `data/legal-authorities/raw/`
- `data/legal-authorities/normalized/`
- `data/legal-authorities/index/`

设计原则：
- 摘要层继续用于人工维护和主题说明
- 原文快照层用于断网访问权威来源
- 标准化文本层用于代码离线检索和摘录

详细方案见：
- [法规原文本地存储方案](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-authority-local-storage-spec.md)

## 9. 规则候选与 benchmark gate

当前已支持自动生成：
- `rule candidates`
- `benchmark gate`

产物目录：
- `docs/generated/improvement/`

用途：
- 让模型新增问题沉淀为候选规则
- 通过 gate 决定是否具备转正式规则的基础

## 10. 对接建议

### 10.1 适合直接对接的场景

- 内部采购审查工作台
- 文件上传与审查结果展示页面
- 规则管理和优化后台
- 批量审查脚本

### 10.2 不建议直接依赖的场景

- 要求强实时外部联网法规检索
- 要求 Word 原生精确页码级跳转
- 要求完全替代人工终审

### 10.3 推荐接入模式

推荐先接：
- `POST /api/review`
- `GET /api/rules`
- `POST /api/rules/decision`

然后再根据需要接：
- 结果落库
- 历史任务
- benchmark 展示
- 差异样本回归

## 11. 版本与扩展建议

建议将系统按以下边界扩展：
- 文档标准化层
- 规则层
- 结构分析层
- 模型辅助层
- 仲裁层
- 输出层
- 规则候选与 gate 层

这样可以避免后续把新能力直接堆到单一函数中。

## 12. 对接时需要知道的边界

- 当前页面和 API 主要服务本地部署场景
- 当前 `review-next` 更适合人工复核，不是对外公开门户
- 当前规则管理页用于“候选规则确认入库”，不是完整运维后台
- 当前长文档 LLM 稳定性仍在持续优化中

## 13. 一句话给技术团队

如果只用一句话向技术团队描述：

“这套系统已经提供了本地可运行的文档标准化、规则审查、章节级问题归并、模型辅助、结构化输出、文档定位和规则候选管理能力，推荐以 CLI 或 Web API 方式接入，并将规则候选与 benchmark gate 作为后续持续优化接口。” 
