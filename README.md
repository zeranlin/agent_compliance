# 政府采购需求合规性检查工作框架

本仓库定义了一套面向政府采购采购需求合规性检查智能体的 harness 化架构。

目标不只是回答“某条款有没有风险”，而是把智能体的工作回路做成可检查、可续跑、可评测、可持续改进的系统。

核心思路：
- 顶层文件负责告诉智能体先看哪里
- 领域规则沉淀在产品规格文档中
- 推理依据和设计取舍沉淀在设计文档中
- 当前工作状态记录在执行计划中
- 质量通过评测样例和反馈产物持续提升

从这里开始：
1. [ARCHITECTURE.md](/Users/linzeran/code/2026-zn/agent_compliance/ARCHITECTURE.md)
2. [openai-harness-notes.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/openai-harness-notes.md)
3. [procurement-compliance-review-workflow.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/procurement-compliance-review-workflow.md)
4. [initial-harness-bootstrap.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/exec-plans/active/initial-harness-bootstrap.md)
5. [local-offline-runtime-roadmap.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/exec-plans/active/local-offline-runtime-roadmap.md)

能力建设重点文档：
- [capability-overview.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/capability-overview.md)
- [full-capability-profile.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/full-capability-profile.md)
- [local-runtime-skeleton.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/local-runtime-skeleton.md)
- [local-codeification-roadmap.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/local-codeification-roadmap.md)
- [code-review-to-human-parity-roadmap.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/code-review-to-human-parity-roadmap.md)
- [legal-authority-system.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/legal-authority-system.md)
- [case-library-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/case-library-design.md)
- [continuous-update-mechanism.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/continuous-update-mechanism.md)
- [consistency-and-caching-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/consistency-and-caching-design.md)

本地执行骨架：
- `setup.py`
- `src/agent_compliance/`
- `tests/`

当前最小可运行命令：
- `PYTHONPATH=src python3 -m agent_compliance normalize <file>`
- `PYTHONPATH=src python3 -m agent_compliance scan-rules <file> --json`
- `PYTHONPATH=src python3 -m agent_compliance review <file> --json`
- `PYTHONPATH=src python3 -m agent_compliance web`

测试阶段默认关闭 review 缓存；如需复用缓存，可显式加：
- `PYTHONPATH=src python3 -m agent_compliance review <file> --json --use-cache`

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
- 当前已补入规则管理区，可查看正式规则数量、候选规则、benchmark gate 状态，并记录“确认入库 / 暂缓 / 忽略”决策

本地引用资料：
- [法规依据本地引用库](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/legal-authorities/README.md)
- [案例口径本地引用库](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/case-sources/README.md)
- [引用资料索引](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/reference-index.md)

更新输出模板：
- [月度规则更新摘要模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/monthly-rule-update-template.md)
- [新增案例候选模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/new-case-candidates-template.md)
- [能力缺口评测报告模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/eval-gap-report-template.md)
- [业务方/采购人修改用正式审查意见表模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/business-facing-review-table-template.md)
- [正式审查意见模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/review-output-template.md)

新增评测样本：
- [LGDL2025000044 人工逼近查点](/Users/linzeran/code/2026-zn/agent_compliance/docs/evals/cases/lgdl2025000044-human-parity-checkpoints.md)
