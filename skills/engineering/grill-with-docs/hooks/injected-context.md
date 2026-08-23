This request looks like it proposes a new feature or a non-trivial design decision. Before writing any implementation code, run the design-interview workflow:

1. Invoke the `grilling` skill and the `domain-modeling` skill (both via the Skill tool).
2. Interview the user with structured questions, one frontier of decisions per round, each question carrying your recommended answer. Find facts yourself (filesystem, tools); put only real decisions to the user. Do not start implementing until the user confirms you have reached shared understanding.
3. As decisions settle, record the resolved design (the design tree, the decisions, and the reasoning behind each) in the repo's planning-doc location. Detect the convention in this order, first match wins:
   - If the repo has a `docs/plans/` tree with `todo/`, `in-progress/`, `finished/` state folders, or a `pdd-protocol.md` file anywhere, follow that protocol and scaffold under `docs/plans/in-progress/<area>/<task>/`.
   - Else if a `docs/superpowers/` directory exists, write the design as `docs/superpowers/specs/<YYYY-MM-DD>-<slug>-design.md`.
   - Else write one file, `docs/plans/<YYYY-MM-DD>-<slug>.md`, holding the resolved design tree, the decisions and why each was made, and the task list.
   Create the file lazily, once the first decision is worth writing down. Keep `CONTEXT.md` a glossary only, and offer an ADR only for decisions that are hard to reverse, surprising without context, and the result of a real trade-off.

If this request is not actually a new feature (it is a bug fix, a question, or a small edit), ignore this and proceed normally.
