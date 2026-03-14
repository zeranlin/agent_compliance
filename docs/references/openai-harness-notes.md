# OpenAI Harness Notes

This file distills the architecture ideas that inform this repository.

Sources:
- [Harness engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/)
- [Unrolling the Codex agent loop](https://openai.com/zh-Hans-CN/index/unrolling-the-codex-agent-loop/)

## What matters for this repository

### Repositories should be navigable by agents

The OpenAI guidance emphasizes that repositories used by agents should be easy to scan and route through. That is why this project uses short top-level maps and pushes detail into deeper docs.

### Plans are externalized state

The agent loop works better when active work is written down. We therefore keep current tasks in `docs/exec-plans/active/` and treat those plans as resumable loop state.

### Feedback loops matter more than one-off brilliance

Harness engineering values fast iteration, structured feedback, and logs over trying to get perfection in a single run. For procurement compliance, that means:
- saving example failures
- converting them into eval cases
- updating specs and prompts from the failures

### Taste still matters

The Codex article also notes that strong outcomes require judgment, not only infrastructure. In this repository, that means the agent should not mechanically flag every specific parameter. It should distinguish:
- legitimate performance need
- suspicious restriction
- clear exclusionary language

### Agent loops need inspectable artifacts

When the loop does work, later loops need to inspect what happened. For this domain, important artifacts include:
- structured findings
- source clause mapping
- unresolved ambiguity notes
- rubric-based eval reports

## Translation into procurement-compliance design

Harness principle -> repo design choice

- agent-readable map -> `AGENTS.md`, `README.md`, `ARCHITECTURE.md`
- externalized loop state -> `docs/exec-plans/`
- product understanding -> `docs/product-specs/`
- deeper rationale -> `docs/design-docs/`
- systematic improvement -> `docs/evals/`
- durable outputs -> `docs/generated/`
