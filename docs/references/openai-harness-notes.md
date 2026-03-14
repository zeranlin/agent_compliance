# OpenAI 工作框架参考笔记

本文件提炼了支撑本仓库设计的核心架构思路。

参考来源：
- [工作框架工程（Harness engineering）](https://openai.com/zh-Hans-CN/index/harness-engineering/)
- [Unrolling the Codex agent loop](https://openai.com/zh-Hans-CN/index/unrolling-the-codex-agent-loop/)

## 对本仓库最重要的点

### 仓库应当能被智能体快速导航

OpenAI 的方法强调：供智能体使用的仓库必须易于扫描、易于路由。因此这个项目采用“顶层地图短小、细节下沉文档”的组织方式。

### 计划是外部化状态

当活动工作被明确写下来时，agent loop 的表现会更好。因此我们把当前任务保存在 `docs/exec-plans/active/` 中，并把这些计划视为可恢复的循环状态。

### 反馈循环比一次性“聪明发挥”更重要

工作框架工程更看重快速迭代、结构化反馈和日志留存，而不是试图一次跑出完美结果。落实到采购合规场景，就是：
- saving example failures
- converting them into eval cases
- updating specs and prompts from the failures

对应中文理解：
- 保存失败样例
- 将失败样例转成 eval 案例
- 根据失败样例反向更新规格和 prompt

### 判断力仍然重要

Codex 的文章也指出，好的结果不仅依赖基础设施，也依赖判断力。在本仓库中，这意味着智能体不应机械地把每个具体参数都判成问题，而应区分：
- legitimate performance need
- suspicious restriction
- clear exclusionary language

对应中文理解：
- 合法的性能需求
- 可疑的限制性要求
- 明显排他性的表述

### Agent loop 需要可检查的产物

当一个 loop 完成工作后，后续 loop 需要能检查之前发生了什么。对这个领域而言，重要产物包括：
- structured findings
- source clause mapping
- unresolved ambiguity notes
- rubric-based eval reports

对应中文理解：
- 结构化 finding
- 原始条款映射
- 尚未解决的歧义说明
- 基于 rubric 的评测报告

## 如何映射为采购合规设计

工作框架原则 -> 仓库设计选择

- agent-readable map -> `AGENTS.md`, `README.md`, `ARCHITECTURE.md`
- externalized loop state -> `docs/exec-plans/`
- product understanding -> `docs/product-specs/`
- deeper rationale -> `docs/design-docs/`
- systematic improvement -> `docs/evals/`
- durable outputs -> `docs/generated/`
