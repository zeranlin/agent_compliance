# Government Procurement Compliance Harness

This repository defines a harness-oriented architecture for a government procurement procurement-needs compliance agent.

The goal is not only to answer whether a clause is risky. The goal is to make the agent loop inspectable, resumable, testable, and steadily improvable.

Core idea:
- top-level files tell an agent where to look
- domain rules live in product specs
- reasoning and tradeoffs live in design docs
- active work is tracked in exec plans
- quality improves through eval cases and feedback artifacts

Start here:
1. [ARCHITECTURE.md](/Users/linzeran/code/2026-zn/agent_compliance/ARCHITECTURE.md)
2. [openai-harness-notes.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/openai-harness-notes.md)
3. [procurement-compliance-review-workflow.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/procurement-compliance-review-workflow.md)
4. [initial-harness-bootstrap.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/exec-plans/active/initial-harness-bootstrap.md)
