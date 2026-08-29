---
name: recording-designs
description: "Write the resolved design record into the repo's planning-doc location, matching whatever planning convention the repo already uses (PDD, Superpowers, or a single default file). Use when an interview or design discussion has settled decisions worth writing down, or when another flow needs to know where a plan or design doc belongs in this repo."
---

# Where the design record lands

The **design record** is the artifact `domain-modeling` does not leave: the resolved design tree with the decisions and the reasoning behind them, and the tasks that fall out of it. It lands in whatever planning-doc convention the repo already uses, so a repo you have set up before keeps its own layout and you carry no location in your head.

Detect the convention in this order, first match wins:

1. **PDD.** A `docs/plans/` tree with `todo/`, `in-progress/`, `finished/` state folders, or a `pdd-protocol.md` file anywhere in the repo. Read that protocol and follow it: scaffold under `docs/plans/in-progress/<area>/<task>/` with the numbered files it prescribes.
2. **Superpowers.** A `docs/superpowers/` directory. Write the design as `docs/superpowers/specs/<YYYY-MM-DD>-<slug>-design.md` and the plan as `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md`.
3. **No convention.** Write one file, `docs/plans/<YYYY-MM-DD>-<slug>.md`, holding the resolved design tree, the decisions and why each was made, and the task list.

Create the file lazily, once the first decision is worth writing down, the same way `domain-modeling` creates `CONTEXT.md`.

## Graduating the default

The single file is the default because a current model holds a whole design doc in context at once, so splitting one plan across many files buys nothing until the work outgrows a single reader. Graduate to the fuller multi-file layout (a separate progress log, a separate task list) only once the work earns it:

- it spans more than one session, so a durable progress log has to carry state across the gap;
- subagents execute it, so each needs the spec and the tasks as their own files to read;
- an external tracker (a ClickUp task, a GitHub issue) owns the work, so the on-disk files become the private working surface beside it.

Until one of those holds, keep it to one file.
