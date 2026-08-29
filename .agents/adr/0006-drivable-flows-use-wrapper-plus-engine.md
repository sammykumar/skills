# Drivable flows get a model-invoked engine, not a flipped flag

`auto-implement` drives the main flow end to end from one command. To reach the work each phase does, it calls **model-invoked engines** (`grilling`, `domain-modeling`, `recording-designs`, `writing-specs`, `splitting-tickets`, `tdd`, `code-review`), never the user-invoked wrappers that carry those phases' names on the map (`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`). Where an engine did not already exist, we extracted one and left the wrapper as a thin shell over it.

## Why

A user-invoked skill is unreachable by anything but the human typing it, and on Claude Code an attempt to call one is refused with an instruction not to reproduce the steps another way, which wastes the turn. That is the same block [ADR 0003](./0003-auto-trigger-injects-sub-skills-not-the-wrapper.md) hit from a hook. Any skill that wants to drive a flow therefore needs a legitimate call target for every phase.

Three of those targets already existed, because the pattern was already here: `grill-with-docs` is a shell over `grilling` and `domain-modeling`, and `implement` is a shell over `tdd` and `code-review`. Extracting `writing-specs`, `splitting-tickets`, and `recording-designs` applies the shape the repo was already using rather than introducing a new one.

## Considered options

- **Flip `disable-model-invocation` on the routed entry skills.** Rejected, for the second time after ADR 0003. Their descriptions carry rich triggers by design (`implement` reads "Implement a piece of work based on a spec or set of tickets"), so flipping the flag makes them fire on ordinary coding prompts in every session. Keeping that in check means rewriting the descriptions to be deliberately un-triggering, which inverts the rule in `invocation.md` that model-invoked descriptions keep rich trigger phrasing. The mitigation costs more than the duplication it saves.
- **Copy each phase's body into `auto-implement`.** Rejected: roughly 180 lines duplicated across two sites, hand-synced forever. `invocation.md` already bans reaching another skill's material by cross-folder link, and names the Skill call as the sanctioned mechanism, which only works against a model-invoked target.
- **Have `auto-implement` stop after grilling and hand back the remaining commands to type.** Rejected as a non-answer: the friction being removed is precisely the hop between phases.

## Consequences

The promoted set grows by four skills: `auto-implement` plus three engines, each needing an `agents/openai.yaml`, a docs page, a `plugin.json` entry, and README rows. The engines are implementation detail with human-facing pages, which is slightly awkward, and their pages say so by naming the wrapper they sit under.

`writing-specs` and `splitting-tickets` are now model-reachable, so the model may publish a spec or tickets to the tracker without being told to. Their descriptions are scoped to the situation rather than to any mention of specs or tickets, which is the only knob available.

ADR 0003's stated cost, hand-syncing the plan-location rules across sites, is retired: those rules are now `recording-designs`, and both callers reach the one copy.
