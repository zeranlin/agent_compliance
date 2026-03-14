# agent_compliance

本仓库按 harness 方式组织，而不是按聊天记录堆叠。

在这里工作时，应优先优化：
- 让后续智能体能够快速读懂
- 顶层文件简短，细节文档下沉链接
- 计划可在中途恢复执行
- 评测产物明确可查
- 采购领域问题可追溯

建议按以下顺序阅读：
1. `README.md`
2. `ARCHITECTURE.md`
3. `docs/references/openai-harness-notes.md`
4. `docs/product-specs/` 下相关文件
5. `docs/exec-plans/active/` 下当前活动计划

仓库约定：
- 顶层文件保持简洁，方便智能体快速扫描。
- 较长的设计理由放在 `docs/design-docs/`。
- 操作流程和业务规范放在 `docs/product-specs/`。
- 当前执行中的工作放在 `docs/exec-plans/active/`。
- 已完成计划移到 `docs/exec-plans/completed/`。
- 生成结果、样例审查和运行产物放在 `docs/generated/`。
- 评测样例、评分规则和报告放在 `docs/evals/`。

对于政府采购合规审查工作，每个有实质内容的输出都应尽量包含：
- 来源条款或证据位置
- 风险类型
- 法律或政策依据（如有）
- 置信度
- 建议的合规改写
- 需要人工采购或法务复核的事项
