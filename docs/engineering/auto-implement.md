## What it does

`auto-implement` drives the whole main flow, from an idea to either working code or a set of tickets, without stopping between phases to ask which skill comes next. You name the feature when you invoke it (`/auto-implement add bulk subject-job creation to the source-scoped media routes`), and it grills you about it, records the resolved design where this repo keeps plans, then takes the single-session or multi-session branch with you and follows it.

It refuses to build tickets. When the grilling concludes the work is multi-session, the skill publishes the spec and the tickets and then stops, because each ticket is meant to be built in its own fresh context window and driving them from here would defeat the split that just happened.

## When to reach for it

- **Invocation mode.** You invoke this by typing `/auto-implement <feature>`, and the agent won't reach for it on its own.
- **Trigger boundary.** Reach for it when you already know the work is ordinary feature work and you want the route walked for you. When you are unsure which route applies at all, ask [ask-sk](../engineering/ask-sk.md) first. When you want to stop and think between phases, or you are picking a flow up part-way through, run the individual skills instead: [grill-with-docs](../engineering/grill-with-docs.md), [to-spec](../engineering/to-spec.md), [to-tickets](../engineering/to-tickets.md), [implement](../engineering/implement.md).

## Prerequisites

A working directory: the skill writes `CONTEXT.md`, ADRs, and a design record into the repo. On the multi-session branch it also publishes to the project issue tracker and applies triage labels, so [setup-sk-skills](../engineering/setup-sk-skills.md) needs to have run in this repo first.

## The branch it makes for you

The one decision the skill makes with you rather than for you is **session count**: whether the design you just settled fits in a single fresh context window and still leaves the model reasoning sharply.

| Branch | What runs | Where it stops |
| --- | --- | --- |
| Single session | Test-driven build one red-green slice at a time, then a two-axis review of the diff, then a commit | After the commit |
| Multi-session | The design becomes a published spec, then tracer-bullet tickets with their blocking edges | Before any ticket is built |

It judges the branch from the design the grilling produced, not from how big the original ask sounded, and it says which way it is leaning before you confirm.

## Why it never names the flow skills

The skill calls `grilling`, `domain-modeling`, `recording-designs`, `writing-specs`, `splitting-tickets`, `tdd`, and `code-review`. It deliberately does not call `/grill-with-docs`, `/to-spec`, `/to-tickets`, or `/implement`, even though those are the names on the map. Those four are user-invoked wrappers, reachable only when you type them, so an attempt to call one is refused and the turn is wasted. Each wrapper is a thin shell over the engine `auto-implement` calls directly, so the work is identical either way.

## Common questions

**Does it skip the interview because I named the feature up front?**
No. The feature description is a starting point for the grilling, not a substitute for it. Naming the feature saves the opening round trip, nothing more.

**Why won't it just build the tickets it created?**
Because it would be carrying this window's whole context into every ticket. The tickets are self-contained by construction, which only pays off if each one starts in a cleared window.

**Can I compact part-way through?**
No. The grilling, the spec, and the tickets all build on the same thinking, so they have to share one unbroken context window. If a session approaches the smart zone before the tickets land, that is a sign the scope was too big for this skill.

## It's working if

- You typed one command and the next thing that happened was an interview, not a question about which skill to run.
- The design record landed in the planning-doc location this repo already used, without you naming a path.
- On the multi-session branch, the run ends with a list of tickets and an instruction to clear, not with code.
- Nothing in the trace shows a refused skill call.

## Where it fits

A **chain driver**: it runs the chain `grill-with-docs → to-spec → to-tickets` (or `grill-with-docs → implement`) as one step rather than four. Its neighbours are [ask-sk](../engineering/ask-sk.md), which you ask when you don't yet know the route this skill assumes, and [wayfinder](../engineering/wayfinder.md), for the effort too foggy to grill in one session at all. [ask-sk](../engineering/ask-sk.md) is the router over the whole set.
