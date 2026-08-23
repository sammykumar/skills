The agent-instruction files for this repo were just edited (`CLAUDE.md`, `AGENTS.md`, or a skill's `agents/*.yaml`). A change to the instructions often shifts the project's shared vocabulary or the way its concepts relate.

1. Invoke the `domain-modeling` skill (via the Skill tool).
2. Reconcile the glossary with what just changed: check whether any term in `CONTEXT.md` now conflicts with the edited instructions, whether a newly introduced concept needs a canonical term, and whether the code still agrees with the glossary. Update `CONTEXT.md` inline as terms resolve, keeping it a glossary and nothing else.
3. This is a lightweight reconciliation nudge, not a design interview. Do not start a grilling. Only offer an ADR for a decision that is hard to reverse, surprising without context, and the result of a real trade-off.

If the edit did not touch the domain vocabulary (a typo, formatting, an unrelated tweak), ignore this and carry on.
