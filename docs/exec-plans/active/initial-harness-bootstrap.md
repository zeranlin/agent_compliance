# Initial Harness Bootstrap

## Goal

Turn `agent_compliance` from an empty folder into a harness-oriented repository for a government procurement compliance agent.

## Current status

Completed:
- created top-level agent map
- created architecture document
- created procurement review workflow spec
- created OpenAI-guidance reference notes
- created design rationale document

Pending:
- define finding schema in detail
- define severity and confidence rubric
- add starter eval cases
- add sample generated review output

## Next actions

1. Create `docs/product-specs/finding-schema.md`.
2. Create `docs/evals/rubrics/review-rubric.md`.
3. Add at least 10 benchmark clauses across clear pass, clear fail, and borderline cases.
4. Add one fully worked sample report under `docs/generated/`.
5. Refine the workflow using failures from the benchmark set.

## Open questions

- Which jurisdiction and policy corpus should be treated as primary authority?
- Should the agent target only procurement-needs review, or also scoring rules and contract clauses?
- What output format is preferred for downstream use: Markdown table, JSON, or both?
