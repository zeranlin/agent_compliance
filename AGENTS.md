# agent_compliance

This repository is organized as a harness, not a chat transcript dump.

When working here, optimize for:
- legibility to future agents
- short top-level files and deeper linked docs
- plans that can be resumed mid-loop
- explicit evaluation artifacts
- procurement-domain traceability

Read in this order:
1. `README.md`
2. `ARCHITECTURE.md`
3. `docs/references/openai-harness-notes.md`
4. relevant files under `docs/product-specs/`
5. active plan under `docs/exec-plans/active/`

Repository conventions:
- Keep top-level files concise and agent-scannable.
- Put long rationale in `docs/design-docs/`.
- Put operating procedures in `docs/product-specs/`.
- Put current execution work in `docs/exec-plans/active/`.
- Move finished plans to `docs/exec-plans/completed/`.
- Store generated outputs, sample reviews, and run artifacts in `docs/generated/`.
- Store evaluation cases, scoring rubrics, and reports in `docs/evals/`.

For government procurement compliance work, every substantive output should make room for:
- source clause or evidence location
- risk type
- legal or policy basis if available
- confidence level
- proposed compliant rewrite
- items requiring human legal or procurement review
