# Repo Design Rationale

This repository is intentionally document-heavy at the start because the current need is architectural alignment, not code volume.

## Why not start with prompts only

Prompt-only systems are brittle for compliance review. They hide assumptions, make iteration hard, and leave weak handoff points for later agent loops.

## Why plans are stored in-repo

Execution plans provide:
- continuity across loops
- visibility into current priorities
- a place to capture scope changes and blockers

## Why evals are part of the first design

Compliance checking fails quietly when no benchmark exists. A repository that only stores prompts will drift. A repository with eval cases can improve deliberately.

## Why this is a harness for procurement compliance

Government procurement review is a good fit for harness engineering because it contains:
- repeatable tasks
- recurring error patterns
- a need for evidence-backed judgments
- a strong requirement for human review at the boundary cases
