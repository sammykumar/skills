## What it does

`grill-with-docs` interviews you about a plan or design until you and the agent share one understanding of it, and writes the vocabulary and the hard decisions into your repo while it does. It is the same interview grill-me runs (a round of questions, then wait, then the next round), pointed at a codebase.

It is **stateful**. Every other grilling skill leaves the session in your head; this one leaves files on disk. A term gets resolved and it lands in `CONTEXT.md` the moment it resolves, not batched at the end. A decision passes three gates and it lands as an ADR. The design you settle lands as a design record in the repo's own planning-doc location. That is the whole difference, and it is also the source of most of the trouble people have with the skill: the artifacts are real files in a real repo, so they can be absent when you expected them, and they can drift when more than one person is writing them.

## When to reach for it

You invoke this by typing `/grill-with-docs`; the agent will not reach for it on its own.

Reach for it at the start of a change, in a repo, when the plan is still fuzzy and the words for the thing are not settled yet. It is the single-session tool. Which grilling skill you want depends on what is in front of you:

| What you have | Reach for |
| --- | --- |
| You aren't working in a working directory at all | grill-me |
| A repo, and a change you can settle in one session | `grill-with-docs` |
| An effort too big to hold in one session (a greenfield build, a large feature) | wayfinder |
| A repo with no domain docs at all, and no particular feature in mind | `grill-with-docs`, aimed at the repo rather than a change |
| A decision blocked on knowledge in someone else's head | to-questionnaire |

The wayfinder split comes down to session count: `/grill-with-docs` for single-session planning, `/wayfinder` for multi-session planning.

## Prerequisites

The skill writes into your repo, so you need to be somewhere it is safe to write. Resolved terms go to a `CONTEXT.md` glossary at the root, or to the relevant context's `CONTEXT.md`, if a `CONTEXT-MAP.md` at the root marks the repo as multi-context. Decisions go to `docs/adr/`. The settled design itself, the plan and the reasoning behind it, goes to a design record placed in whatever planning-doc convention the repo already uses (a single file by default when the repo has none). All three are created lazily; nothing exists until the first term, decision, or design point crystallises, so there is nothing to scaffold up front.

It also needs two other skills present, because its own `SKILL.md` is one line that delegates to them: grilling supplies the interview, domain-modeling supplies the writing. Installing `grill-with-docs` alone gets you a skill that does not work.

## The paper trail

Four things can come out of a session, and they are not equal.

| What resolved | Where it lands |
| --- | --- |
| A term: the project's own word for a thing | `CONTEXT.md`, inline, the moment it resolves |
| A decision that is hard to reverse, surprising without context, and a real trade-off | An ADR under `docs/adr/` |
| The settled design: the plan you agreed and the reasoning behind it | A design record, placed by detect-and-match into the repo's own planning-doc convention |
| Nothing worth writing down | The conversation |

That third row used to be missing, and its absence is what caught people out: the design you settled lived only in the context window you settled it in. It now has a home. The record is the resolved design tree with the decisions and the reasoning that produced them, and it lands wherever the repo already keeps planning docs, so a repo you have set up before keeps its own layout. The default is a single dated file; it graduates to a fuller multi-file layout only once the work earns it:

- it spans more than one session;
- subagents execute it, so each needs its own file to read;
- an external tracker (a ClickUp task, a GitHub issue) owns the work.

Like `CONTEXT.md`, the record is created lazily, once the first decision is worth writing down.

The design record does not blur the other two. `CONTEXT.md` stays a glossary and is deliberately kept as one: no implementation details, no spec, no scratch notes. ADRs stay gated on all three conditions at once, so most decisions do not qualify and most sessions produce none; a session that yields a sharper glossary and zero ADRs is still working as designed. What changed is that the reasoning between those two extremes now has somewhere to go. Hand the same conversation to to-spec rather than clearing it, and the design record is what to-spec builds on.

The glossary is the point. Domain language is the thing this skill is actually building: the project's own words, agreed once, so you, the agent and your colleagues stop paying to re-derive them. It is worth saying that not everyone agrees this buys you agent performance: the sharpest public pushback is that a term and its plain-English expansion get the same result from the model, and that the vocabulary really compresses communication between the humans who share it. That reading still leaves the glossary valuable; it just moves the value.

## Common questions

**Should I use this or `/wayfinder`?**
Scope decides it. Use this for anything you can settle in one session; use wayfinder when the effort is too big to hold in one, and it charts the work as a map of decision tickets first. Wayfinder is slower and denser, and reaching for it on a well-scoped feature is the common mistake. It does not replace this skill: it can drop into a grilling session for the parts of the map that suit one.

**It ran, but no `CONTEXT.md` and no ADRs appeared.**
Two known causes. The mundane one: nothing qualified. ADRs need all three gates, and a session about a change with no new vocabulary genuinely has nothing to write. The real bug: when the skill runs inside another orchestration layer (a spec-driven-development wrapper, a multi-agent framework, a rule that invokes it as a step in someone else's pipeline), the file-writing half is reported to silently not happen, while the interview still runs. This is filed and unfixed. If you are in that setup, check the working directory before you trust the session's output.

**It asked everything at once, with no recommendations, and never mentioned `CONTEXT.md`.**
That is the skill failing to load its two dependencies. Because `SKILL.md` is a one-line delegation, an agent that does not pick up grilling and domain-modeling guesses at what grilling means, and you get an undifferentiated question dump. Partial loading is the more confusing case: `grilling` loads, `domain-modeling` does not, and you get a good interview with no paper trail. It correlates with model and effort level, and it is the most reported problem with this skill. If you suspect it, ask the agent directly which skills it loaded.

**Where did all my other decisions go?**
Into the design record. The settled plan and the reasoning behind it now land in the repo's planning-doc location, matched to whatever convention the repo already uses, so the design no longer lives only in the conversation. This was the skill's most substantive open complaint, because the glossary is not a spec and most answers do not earn an ADR. The record complements, rather than replaces, feeding the session to to-spec: keep the session and hand it straight on, and re-read the resulting spec against your own answers, because precise answers (ordering guarantees, negative requirements, numeric defaults) can still get softened into weaker prose downstream.

**Can I point it at an existing repo that has no docs at all?**
Yes. This is the right skill for a codebase with no ADRs, no domain language and no design principles: invoke it and say "help me document my repo". The community pattern pairs it with improve-codebase-architecture for building or repairing a `CONTEXT.md`. Expect to steer it: it will read code and ask you about what it finds, and you are the one who says which of the words already in the codebase are the right ones.

**What should I do when the session ends?**
The skill's closing message tends to be open-ended, which is a known rough edge. In the main flow the answer is to-spec, in the same conversation. If the change is small enough to build immediately, go straight to implement instead.

**Why is it called that?**
Nobody is happy with the name. There is an open suggestion to rename it `grill-domain-model`, which describes the behaviour more honestly. Nothing has moved on it. If a rename ever lands, the docs page moves with it and the URL changes.

## It's working if

- `CONTEXT.md` changes *during* the session, term by term, rather than appearing in one lump at the end.
- The glossary reads as pure vocabulary (your project's words with tight definitions) and contains no implementation detail or spec-like prose.
- Questions the codebase can answer get answered by reading the codebase, not asked of you.
- You get few or no ADRs, and the ones you get are decisions you would be annoyed to have to re-litigate.
- A design record appears in the planning-doc location your repo already uses (a single dated file when it has no convention), holding the plan you settled and why, not just the glossary.
- It challenges a word you used because your existing glossary defines it differently.

## Where it fits

`grill-with-docs` is the head of the main build chain:

```txt
grill-with-docs → to-spec → to-tickets → implement → code-review
```

It comes before anything is written down as a spec: it produces the shared understanding and settled vocabulary that to-spec then synthesises without interviewing you again. Its close neighbours are grill-me, the same interview with no repo and no files, and domain-modeling, the glossary-and-ADR discipline it drives; both sit on the grilling primitive. Upstream of it, wayfinder charts efforts too large for one session and can hand parts of the map back down to it. When you're unsure which skill or flow fits, ask-sk routes you.
