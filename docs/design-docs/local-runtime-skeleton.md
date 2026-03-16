# 本地执行引擎第一阶段骨架

## 目标

在不破坏现有文档型 harness 结构的前提下，为本仓库补齐一层可本地运行的执行引擎骨架，使后续能够逐步把审查能力代码化、离线化，并减少大模型调用。

## 设计原则

- 文档和知识库仍保留在当前仓库，不拆分到新项目。
- 先实现“确定性能力”，再接入本地模型。
- 先实现“规则初筛”，再实现“检索增强判断”。
- 先保证本地可运行，再逐步补强精度和覆盖面。

## 目录结构

```text
setup.py
src/
  agent_compliance/
    __init__.py
    __main__.py
    cli.py
    config.py
    schemas.py
    parsers/
    pipelines/
    rules/
    knowledge/
    cache/
    evals/
tests/
```

## 第一阶段范围

第一阶段不追求完整复刻当前全部人工审查能力，重点完成以下最小闭环：

1. 本地文件抽取和标准化
2. 基于规则的高频风险初筛
3. 结构化 findings 和 Markdown 结果输出
4. 本地 CLI 入口
5. 后续可接本地模型和检索层的模块边界

## CLI 命令

当前骨架包含以下命令：

- `PYTHONPATH=src python3 -m agent_compliance normalize <file>`
- `PYTHONPATH=src python3 -m agent_compliance scan-rules <file>`
- `PYTHONPATH=src python3 -m agent_compliance review <file>`
- `PYTHONPATH=src python3 -m agent_compliance eval`
- `PYTHONPATH=src python3 -m agent_compliance web`

## 当前能力与后续补强关系

### 当前已落地

- `parsers/`: 文本抽取和基础条款切分
- `parsers/section_splitter.py`: 已可输出层级化 `section_path`、`source_section` 和 `table_or_item_label`
- `parsers/pagination.py`: 已可生成 `page_map`，并为 finding 回填 `page_hint`
- 复杂评分表已支持区分“语义标签”和“普通列头”，减少 `section_path` 噪声
- `rules/`: 资格、评分、技术、合同四类高频规则
- `pipelines/normalize.py`: 标准化输出
- `pipelines/rule_scan.py`: 规则命中结果
- `knowledge/references_index.py`: 本地引用资料检索
- `pipelines/review.py`: 第二阶段 finding 组装，已可消费本地规则映射和引用资料
- `pipelines/review.py`: 已支持同区段、同类问题的相邻命中聚合，减少重复 findings
- `pipelines/review.py`: 已可为聚合后的 finding 生成问题标题和统一改写建议
- `cache/review_cache.py`: 已支持 review 结果缓存和缓存命中复用
- `review` 命令现支持显式缓存开关，测试阶段默认关闭缓存，避免影响验证
- review 后处理已可压缩过长 `section_path`，并去掉投标文件格式附件中的重复技术参数 finding
- review 后处理已可将长 `source_text` 压成代表性摘录，并将跨章节重复的同类技术参数归并为更少的主 finding
- 已预留本地大模型兜底接口，兼容 OpenAI 风格 `/v1/chat/completions`，默认关闭
- `web/`: 已具备本地页面，支持上传文件、切换缓存与本地模型开关、浏览审查结果；对 `docx` 优先按段落/表格结构渲染原文，并按 finding 跳转到对应位置
- `pipelines/render.py`: Markdown 和 JSON 落盘
- `tests/test_smoke.py`: CLI 冒烟测试

### 后续优先补强

- 显式分页标记提取与页码映射精度
- 复杂表格结构定位精度
- 本地法规和案例全文检索排序能力
- 规则映射到更细粒度法规依据和案例依据
- 本地模型边界判断与改写建议
- findings 缓存和增量复审
- benchmark 自动跑分

## 为什么先做规则骨架

因为离线运行和减少模型调用的关键，不是先部署更大的模型，而是先把以下能力代码化：

- 文档标准化
- 规则命中
- 本地知识索引
- 结果缓存

只有这四层先稳住，后续本地模型才会变成“少量复杂条款的兜底判断器”，而不是“整篇文档自由推理器”。
