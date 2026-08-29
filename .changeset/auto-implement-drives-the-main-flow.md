---
"sk-skills": patch
---

Add `/auto-implement <feature>`, which drives the main flow end to end from a feature you name up front: it grills the idea, records the resolved design where the repo keeps plans, then either builds it test-first in one session or publishes a spec and tracer-bullet tickets and stops before building them.

To give it something legitimate to call at every phase, three engines were extracted, following the wrapper-and-engine shape already used by `/grill-with-docs` and `/implement`:

- `writing-specs`, the engine under `/to-spec`
- `splitting-tickets`, the engine under `/to-tickets`
- `recording-designs`, holding the design-record location rules previously in `grill-with-docs/PLAN-LOCATION.md`, now shared by `/grill-with-docs` and `/auto-implement`

`/to-spec`, `/to-tickets`, and `/grill-with-docs` behave exactly as before; each is now a thin wrapper over its engine. `ask-sk` routes to `/auto-implement` as the fast path along the main flow.
