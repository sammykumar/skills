## What it does

`writing-specs` turns what has already been discussed into a spec and publishes it to the project issue tracker. It does not interview you: everything it writes comes from the conversation and the codebase it can read.

It is the engine under [to-spec](../engineering/to-spec.md). The two do the same work; the difference is only who can reach them.

## When to reach for it

- **Invocation mode.** Type `/writing-specs`, or the agent reaches for it automatically when a flow arrives at the point where settled thinking should become a published spec.
- **Trigger boundary.** Reach for it when the design is already settled and needs writing up. If the design is not settled yet, grill it first. If you want to type the command yourself, [to-spec](../engineering/to-spec.md) is the name on the map and behaves identically.

## Prerequisites

[setup-sk-skills](../engineering/setup-sk-skills.md) must have configured the issue tracker and the triage label vocabulary: the skill publishes the spec and applies the `ready-for-agent` label, and without the mapping the output goes to the wrong place.

## Seams before prose

Before it writes anything, the skill sketches the **seams** the feature will be tested at, prefers existing seams to new ones, takes the highest seam available, and checks that choice with you. The fewer seams a change introduces, the better; one is ideal. That check is the only place it asks you anything.

## Why this skill exists separately

[to-spec](../engineering/to-spec.md) is user-invoked, so nothing but you can fire it. That is deliberate, but it means a driver like [auto-implement](../engineering/auto-implement.md) has no way to reach the work. Splitting the body out into a model-invoked skill gives the driver a legitimate call and keeps one source of truth, instead of a second copy of the spec template drifting out of sync.

## It's working if

- The spec arrives without you being interviewed a second time about things you already decided.
- The user stories section is long and covers the feature from the user's side, not the implementation's.
- No file paths or code snippets appear in it, except where a prototype produced a snippet that pins a decision down.

## Where it fits

A **chain step**, and the engine half of one: `grill-with-docs → to-spec → to-tickets → implement`. Its neighbours are [to-spec](../engineering/to-spec.md), the wrapper you type, and [splitting-tickets](../engineering/splitting-tickets.md), which takes the spec it publishes and slices it. [ask-sk](../engineering/ask-sk.md) is the router over the whole set.
