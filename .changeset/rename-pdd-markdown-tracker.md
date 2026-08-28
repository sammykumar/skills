---
"sk-skills": minor
---

Rename the local-markdown issue tracker to "Repo PDD Markdown (Plan-Driven Development)" across `/setup-sk-skills`, its tracker template, and the downstream skills and docs. `/setup-sk-skills` now sweeps for a repo's existing canonical plan/docs directory (`docs/plans/`, `docs/plan/`, `plans/`, `plan/`, `docs/specs/`, `specs/`, `.scratch/`) and reuses the first it finds, falling back to `docs/plans/` when none exists instead of hardcoding `.scratch/`. The tracker template is parameterized with a `{{PLAN_DIR}}` token the skill substitutes with the resolved directory; `.scratch/` stays recognized for backward-compat.
