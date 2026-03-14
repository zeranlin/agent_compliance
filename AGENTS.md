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

交付约定
- 每次执行都在仓库留下痕迹（文档/提交/日志）。
- Git 提交信息必须使用“结论式提交”，直接体现本次改动完成了什么、现在具备了什么结果，不要只写技术动作或实现过程。
- 完成一个完整阶段结果后，默认自动 `commit` 并自动 `push`；除非用户明确要求仅保留本地提交。
- 不明确的高风险操作先请求确认。
- 完成后提供清晰的“做了什么 + 下一步”。
- 如能力发生明显更新，应同步更新 [capability-overview.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/capability-overview.md)。
- 对同一文件复审时，在输入、规则、引用状态和输出格式未变化的前提下，应尽量保持审查结果一致；如结论变化，必须说明变化原因。
- 后续复审默认优先复用标准化输入、规则命中结果和结构化 findings 缓存，仅对受影响条款重新调用大模型，不对整份文档重复进行全量自由推理。
