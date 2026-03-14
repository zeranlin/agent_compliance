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

能力建设重点文档：
- [legal-authority-system.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/legal-authority-system.md)
- [case-library-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/case-library-design.md)
- [continuous-update-mechanism.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/continuous-update-mechanism.md)

本地引用资料：
- [法规依据本地引用库](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/legal-authorities/README.md)
- [案例口径本地引用库](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/case-sources/README.md)
- [引用资料索引](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/reference-index.md)
