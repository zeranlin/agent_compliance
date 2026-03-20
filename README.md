# 采购需求合规性检查智能体工作框架

本仓库定义了一套面向政府采购场景的“采购需求合规性检查智能体” harness 化架构。

目标不只是回答“某条款有没有风险”，而是帮助采购人在采购需求形成、复核和发布前，尽早发现可能影响公平竞争、履约边界、验收可执行性和合同平衡性的风险，并把智能体的工作回路做成可检查、可续跑、可评测、可持续改进的系统。

当前阶段重点：
- 帮助采购人在发布前发现风险
- 帮助采购人完成改稿和复核
- 帮助采购人更放心地把采购需求进行公布

当前暂不优先扩展为：
- 发布后的争议裁判
- 投标文件评审裁判
- 履约争议归责系统

核心思路：
- 顶层文件负责告诉智能体先看哪里
- 领域规则沉淀在产品规格文档中
- 推理依据和设计取舍沉淀在设计文档中
- 当前工作状态记录在执行计划中
- 质量通过评测样例和反馈产物持续提升

从这里开始：
1. [ARCHITECTURE.md](https://github.com/zeranlin/agent_compliance/blob/main/ARCHITECTURE.md)
2. [openai-harness-notes.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/openai-harness-notes.md)
3. [procurement-compliance-review-workflow.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/procurement-compliance-review-workflow.md)
4. [initial-harness-bootstrap.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/exec-plans/active/initial-harness-bootstrap.md)
5. [local-offline-runtime-roadmap.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/exec-plans/active/local-offline-runtime-roadmap.md)

能力建设重点文档：
- [capability-overview.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/capability-overview.md)
- [full-capability-profile.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/full-capability-profile.md)
- [code-review-system-technical-description.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-system-technical-description.md)
- [local-runtime-skeleton.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/local-runtime-skeleton.md)
- [local-codeification-roadmap.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/local-codeification-roadmap.md)
- [code-review-to-human-parity-roadmap.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-to-human-parity-roadmap.md)
- [code-review-gap-closure-roadmap.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-gap-closure-roadmap.md)
- [continuous-human-parity-architecture.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/continuous-human-parity-architecture.md)
- [procurement-catalog-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/procurement-catalog-layer-design.md)
- [code-review-main-pipeline-update.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-main-pipeline-update.md)
- [architecture-gap-priorities.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/architecture-gap-priorities.md)
- [engine-tuning-checklist.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/engine-tuning-checklist.md)
- [procurement-risk-identification-priorities.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/procurement-risk-identification-priorities.md)
- [human-vs-code-review-gap-matrix.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/human-vs-code-review-gap-matrix.md)
- [legal-semantic-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-semantic-layer-design.md)
- [legal-authority-local-storage-spec.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-authority-local-storage-spec.md)
- [review-export-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/review-export-design.md)
- [review-check-progress-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/review-check-progress-design.md)
- [effective-requirement-scope-filter-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/effective-requirement-scope-filter-design.md)
- [requirement-scope-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/requirement-scope-layer-design.md)
- [tender-document-risk-scope-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/tender-document-risk-scope-layer-design.md)
- [tender-document-parser-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/tender-document-parser-design.md)
- [budget-demand-agent-architecture.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/budget-demand-agent-architecture.md)
- [repo-layered-architecture.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/repo-layered-architecture.md)
- [agent-incubation-and-distillation-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/agent-incubation-and-distillation-design.md)
- [llm-fast-path-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/llm-fast-path-design.md)
- [legal-authority-system.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/legal-authority-system.md)
- [case-library-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/case-library-design.md)
- [continuous-update-mechanism.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/continuous-update-mechanism.md)
- [consistency-and-caching-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/consistency-and-caching-design.md)

产品与对接文档：
- [code-review-product-introduction.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/code-review-product-introduction.md)
- [code-review-technical-integration.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/code-review-technical-integration.md)

本地执行骨架：
- `setup.py`
- `src/agent_compliance/`
- `tests/`

当前最小可运行命令：
- `PYTHONPATH=src python3 -m agent_compliance normalize <file>`
- `PYTHONPATH=src python3 -m agent_compliance scan-rules <file> --json`
- `PYTHONPATH=src python3 -m agent_compliance review <file> --json`
- `PYTHONPATH=src python3 -m agent_compliance review <file> --json --tender-parser-mode assist`
- `PYTHONPATH=src python3 -m agent_compliance incubate-agent <agent_key>`
- `PYTHONPATH=src python3 -m agent_compliance web`

测试阶段默认关闭 review 缓存；如需复用缓存，可显式加：
- `PYTHONPATH=src python3 -m agent_compliance review <file> --json --use-cache`

招标文件独立解析器当前已支持可配置前置：
- 环境变量：`AGENT_COMPLIANCE_TENDER_PARSER_MODE=off|assist|required`
- CLI：`--tender-parser-mode off|assist|required`
- 当前推荐先使用 `assist`

智能体孵化与蒸馏工厂当前已支持：
- 标准蓝图：`review_agent`、`budget_agent`、`demand_research_agent`
- 标准命令：`PYTHONPATH=src python3 -m agent_compliance incubate-agent <agent_key>`
- 标准产物：
  - `*-distillation-report.md`
  - `*-distillation-report.json`
  - `*-run.json`
- 当前已用 `政府采购需求调查智能体` 跑通第一轮真实 MVP 孵化验证，产物位于：
  - `docs/generated/incubator/demand_research/`
- 当前也已支持最小自动对照生成：
  - `--human-baseline-file`
  - `--strong-agent-result-file`
  - `--target-agent-result-file`
  用于把三份标准文本自动转换成一条 `ValidationComparison`

本地大模型兜底接口已预留，默认关闭；如需显式启用：
- `PYTHONPATH=src python3 -m agent_compliance review <file> --json --use-llm`
- 可选覆盖模型和地址：`--llm-model <model>`、`--llm-base-url <base_url>`
- 当本地模型启用时，当前会额外执行三类局部判断：
  - 模板错贴与标的域不匹配
  - 评分结构判断
  - 商务链路联合判断
- 同时自动产出：
  - `docs/generated/improvement/*-rule-candidates.{json,md}`
  - `docs/generated/improvement/*-benchmark-gate.{json,md}`
- 当前模型调用已支持自动探测 `/v1/models` 并在默认模型失效时回退到服务端可用模型。

本地 Web 页面：
- 启动：`PYTHONPATH=src python3 -m agent_compliance web`
- 默认地址：[http://127.0.0.1:8765](http://127.0.0.1:8765)
- 当前支持上传文件、启用缓存/本地模型开关、查看审查摘要和 findings 列表；对 `docx` 会优先按段落/表格结构渲染原文，并按 finding 跳转定位到对应位置
- 当前已补入采购人视角页面 `/review-check`，更偏正式审查意见和改稿工作台视角，弱化实验性信息，只保留问题导航、原文定位、法规依据、建议改写和导出
- 当前已补入规则管理区，可查看正式规则数量、候选规则、benchmark gate 状态，并记录“确认入库 / 暂缓 / 忽略”决策
- `review-next` 已开始支持审查结果导出，当前提供 `Markdown / Excel / JSON` 和 `主问题版 / 完整明细版`
- 导出产物会同步写入 `docs/generated/exports/`
- Excel 导出已包含摘要页、冻结首行、自动筛选和按风险等级着色，便于业务和法务直接复核
- 当前导出默认按“采购需求形成与发布前审查”场景组织，优先服务采购人改稿和发布前复核

本地引用资料：
- [法规依据本地引用库](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/legal-authorities/README.md)
- [案例口径本地引用库](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/case-sources/README.md)
- [引用资料索引](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/reference-index.md)

本地品目知识：
- [采购品目目录层设计方案](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/procurement-catalog-layer-design.md)
- `data/procurement-catalog/catalogs.json`

更新输出模板：
- [月度规则更新摘要模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/monthly-rule-update-template.md)
- [新增案例候选模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/new-case-candidates-template.md)
- [能力缺口评测报告模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/eval-gap-report-template.md)
- [业务方/采购人修改用正式审查意见表模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/business-facing-review-table-template.md)
- [正式审查意见模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/review-output-template.md)

新增评测样本：
- [LGDL2025000044 人工逼近查点](https://github.com/zeranlin/agent_compliance/blob/main/docs/evals/cases/lgdl2025000044-human-parity-checkpoints.md)
