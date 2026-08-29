## What it does

`recording-designs` writes the **design record**, the resolved design tree with its decisions and the reasoning behind them, into wherever this repo already keeps plans. It never invents a location: it detects the repo's existing planning convention and matches it, so a repo you set up months ago keeps its own layout and you carry no path in your head.

It creates the file lazily, once the first decision is worth writing down, rather than scaffolding an empty document at the start.

## When to reach for it

- **Invocation mode.** Type `/recording-designs`, or the agent reaches for it automatically once a design discussion has settled decisions worth writing down.
- **Trigger boundary.** Reach for it when the question is *where does this plan belong in this repo*. For the vocabulary in the plan rather than its location, use [domain-modeling](../engineering/domain-modeling.md), which owns `CONTEXT.md` and ADRs.

## Prerequisites

A working directory, since the whole skill is about finding the right place in it.

## The detection order

First match wins.

| Convention | How it is detected | Where the record lands |
| --- | --- | --- |
| PDD | A `docs/plans/` tree with state folders, or a `pdd-protocol.md` anywhere in the repo | Under `docs/plans/in-progress/<area>/<task>/`, following that protocol |
| Superpowers | A `docs/superpowers/` directory | Split across that tree's `specs/` and `plans/` folders |
| None | Neither of the above | A single file under `docs/plans/` |

The single file is the default on purpose. A current model holds a whole design doc at once, so splitting one plan across many files buys nothing until the work outgrows a single reader. The record graduates to a fuller layout only when it earns it: the work spans sessions, subagents execute it, or an external tracker owns it.

## Why this skill exists separately

The rules used to live inside [grill-with-docs](../engineering/grill-with-docs.md) as a pointed-at file. Once [auto-implement](../engineering/auto-implement.md) needed the same rules, a second copy was the alternative, and a copy of a detection order is exactly the thing that goes stale without anyone noticing. Extracting it makes both callers reach the same source.

## It's working if

- The design record appears in the layout the repo was already using, without you naming a path.
- Nothing is written until there is a real decision to write.
- A repo with no planning convention gets one file, not a scaffolded tree.

## Where it fits

A **shared engine** underneath two flows: [grill-with-docs](../engineering/grill-with-docs.md) and [auto-implement](../engineering/auto-implement.md) both call it for the same job. Its neighbour is [domain-modeling](../engineering/domain-modeling.md), which writes the other artifacts of a grilling session, the glossary and the ADRs, while this one writes the plan. [ask-sk](../engineering/ask-sk.md) is the router over the whole set.
