## What it does

`setup-sk-skills` answers four questions about one repo: where issues live, what the triage labels are called, where the domain docs sit, and what you actually call things. The first three are recorded as markdown files under `docs/agents/`. The fourth is different in kind: it reads your past sessions in this repo and proposes glossary terms for `CONTEXT.md`.

Those files are the only thing that varies between repos. The skills themselves are identical everywhere; they read `docs/agents/issue-tracker.md` at run time and do what it says. That is why the set is not tied to GitHub, and why no skill file ever needs editing to point it somewhere else. Invoking it with "link the skills to a custom issue tracker" works with anything you can connect to programmatically, with zero changes to the skills.

It is a prompt-driven skill rather than a deterministic script (the one exception is the vocab miner, which is a real script because transcripts are too large to read by hand). It reads your `git remote`, your existing `CLAUDE.md`, your existing `CONTEXT.md`, proposes what it found, and waits for you to confirm before writing anything.

## When to reach for it

You invoke this by typing `/setup-sk-skills`; the agent won't reach for it on its own. It is deliberately marked non-invokable, so no other skill can fire it for you.

Reach for it once per repo, before the first use of any other engineering skill. If triage, to-spec, to-tickets or wayfinder start guessing where your issues go, or apply labels your tracker doesn't have, they have not been set up here yet. A repo already halfway through a project is a fine place to run it; the skill reads what is already there and no earlier work is wasted.

## Prerequisites

It writes into the repo you run it in:

| It writes | Where |
| --- | --- |
| `issue-tracker.md` | `docs/agents/` |
| `domain.md` | `docs/agents/` |
| `triage-labels.md` | `docs/agents/`, only when the `triage` skill is installed |
| An `## Agent skills` block | whichever of `CLAUDE.md` / `AGENTS.md` already exists |
| Glossary terms you confirmed | `CONTEXT.md`, only if you opted into vocab mining and kept something |

All of it is committed markdown. There is no user-level or global mode: the config lives in the repo, so every repo gets its own copy.

## The four decisions

It leads each section with the recommended answer, and skips whatever exploration already settled. On a fresh repo with no history that is two confirmations and done; on a repo you have been working in, the vocab section adds one more.

| Decision | What it proposes | When it actually asks |
| --- | --- | --- |
| **Issue tracker** | the one matching your `git remote` | always: this is the one real choice |
| **Triage labels** | keep the five canonical names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) | only if the `triage` skill is installed |
| **Domain docs** | single-context: one `CONTEXT.md` plus `docs/adr/` at the root | only if it spots monorepo signals, and then it offers a multi-context `CONTEXT-MAP.md` |
| **User vocab** | mine your past sessions for the words you actually use | only if this repo has past sessions, and then it tells you how many |

The tracker options:

| Option | Where issues live | Needs |
| --- | --- | --- |
| **GitHub** | the repo's GitHub Issues | the `gh` CLI |
| **GitLab** | the repo's GitLab Issues | the `glab` CLI |
| **Repo PDD Markdown** | files under `docs/plans/<feature>/` in this repo | nothing: no remote at all |
| **Other** | wherever you say | one paragraph from you describing the workflow |

The first three ship as templates in the skill and work out of the box. Repo PDD Markdown is a first-class option, not a fallback: a solo project with no remote is fully supported. One caveat is worth repeating: don't use Repo PDD Markdown if you're using GitHub. They are alternatives, not layers.

"Other" is not a stub either. It is the reason Jira, Linear, Azure DevOps and Beads all work: you describe the workflow, the skill records your prose in `docs/agents/issue-tracker.md`, and the downstream skills follow the prose. The community has already done this: a Jira-over-MCP variant, a Gitea CLI shaped like `gh`, a hand-built local dashboard.

## Mining your vocabulary

By the time you onboard a repo there are usually dozens of past sessions in it, and in all of them you have been naming things. That language is on disk and nothing has ever read it. Section D does: it reads your Claude Code transcripts under `~/.claude/projects/` and your Codex rollouts under `~/.codex/sessions/`, keeps only the turns you typed, and ranks the phrases you repeat.

Three things make the ranking worth reading rather than a word-frequency dump:

- **Spread beats repetition.** A phrase used ten times in one long session is jargon of the moment. One used across five separate sessions is real vocabulary, and scores higher.
- **The codebase is a witness.** A phrase that also appears in your file names and code is a grounded domain noun, and gets a boost over one that only ever appears in chat.
- **Synonyms cluster.** Transcripts are the one place you can watch yourself call the same thing three names. The strongest becomes the proposed term and the rest become its `_Avoid_` line, which is the part the codebase could never have told you.

Nothing is written without you confirming it, and the miner itself writes nothing at all: the shortlist goes to stdout and dies with the process, so old transcripts with pasted keys or other people's names cannot leak into a commit. Terms already in your `CONTEXT.md`, and anything already listed under an `_Avoid_`, are filtered out before you see the list, so re-running setup is additive rather than a re-litigation.

## Common questions

**Do I have to use GitHub?**

No. GitHub, GitLab and Repo PDD Markdown under `docs/plans/` all ship as ready-made templates, and anything else works through the "other" path. This is the most-repeated question in the record, in roughly these words: *"hard locked to github"*, *"can I use GitLab / Jira"*, *"what about Azure DevOps"*. The answer every time is that the tracker is a setup answer, not a skill property.

**Do I need to re-run it after updating the skills?**

Asked directly after v1.1, the maintainers said yes. The skill's own closing message is softer: it tells you re-running is only needed to switch trackers or start over. Both are defensible and the reason for the gap is real: the seed templates change between versions, so a `docs/agents/issue-tracker.md` written by an older release can go stale against the skills now reading it. If a downstream skill starts doing something the docs describe differently, re-running is the cheap fix.

**It wrote to `CLAUDE.md`, but I'm on Codex.**

Known gap, still open. The file-selection rule is "edit `CLAUDE.md` if it exists, else `AGENTS.md`": it checks which file exists, not which harness is running. A repo with a `CLAUDE.md` left over from Claude Code will get its `## Agent skills` block somewhere Codex never reads. Two workarounds are in circulation: move the block to `AGENTS.md` by hand, or keep `AGENTS.md` canonical and make `CLAUDE.md` a one-line pointer at it. If neither file exists, the skill asks you which to create rather than picking, which has confused people who expected it to just decide.

**It didn't create my triage labels.**

It doesn't. `docs/agents/triage-labels.md` is a *mapping*: it tells `/triage` which strings in your tracker correspond to the five canonical roles. It does not run `gh label create`. On a fresh GitHub repo the labels genuinely do not exist yet, and this has been filed as a bug more than once. Two follow-ons:

- If your tracker already uses the canonical names, the mapping is an identity table and there is nothing to configure. That is the intended common case, not a missing step.
- wayfinder's `wayfinder:map` and `wayfinder:<type>` labels are not created here either, and `gh issue create --label <missing>` fails outright rather than creating the label. Create them by hand before the first wayfinder run on a GitHub repo.

**The shortlist is full of things I never said.**

Some of it will be. The ranking is n-grams over your typed turns, and it cannot tell your words from an automation's. On a repo where a bot posts into sessions (a tracker comment relay, a scheduled agent), that phrasing arrives in the user role and ranks well because it repeats. The skill is told to read the evidence quotes and drop the machine-written ones before proposing, and to say how many it dropped. If a whole run reads like harness prose rather than your own, the filter list in `mine-vocab.mjs` has gone stale against a transcript format that changed.

**Does it read sessions from my worktrees?**

Yes. Claude Code names its session directory after the working directory, so every git worktree gets its own. The miner derives the slug from where you run it and prefix-matches, which picks up the worktree directories too. Codex stores rollouts flat by date and records the working directory inside each one, so those are matched by path instead. Both are read newest-first and capped, and the run reports how many sessions it skipped rather than truncating quietly.

**Can I configure the other skills' behaviour here (grilling cadence, question format, tone)?**

No. It configures three things (tracker, labels, doc layout) and seeds a fourth (your glossary), and that is the whole surface. There have been direct requests to make it the home for per-user preferences, and the standing answer is that skills stay opinionated: *"Config is death."* Preferences belong in your `CLAUDE.md` as plain instructions, which every skill already reads.

**Can I keep the config in `~/.claude` instead of committing it to every repo?**

Not today. There is an open request for exactly this from someone running the skills across many repos, and no user-level mode exists. Every repo carries its own `docs/agents/`.

**Isn't it strange to have a skill that configures the other skills?**

One long-standing complaint says yes, in these words: *"having a skill to set up the other skill does not feel right to me: that means the LLM is configuring its own skills."* The trade is real and acknowledged: the alternative to a setup step is duplicating tracker instructions into every skill that touches issues. The output is inspectable, editable markdown, which is the mitigation: you can read every file it wrote and change it by hand, and day-to-day tweaks are exactly that, not another run.

## It's working if

- `docs/agents/issue-tracker.md` and `docs/agents/domain.md` exist, plus `triage-labels.md` if `triage` is installed.
- An `## Agent skills` section appears in the instruction file your harness actually reads, with a one-line summary pointing at each of those files.
- The tracker it proposed matches the remote you really use, and the label strings match labels that really exist in your tracker.
- Afterwards, `/to-tickets` publishes without asking you where issues live, and `/triage` applies labels rather than inventing them.
- If you opted into vocab mining and kept some terms, `CONTEXT.md` holds exactly those and nothing you did not confirm.
- Nothing in the skill files themselves changed. If setup edited a `SKILL.md`, something went wrong.

## Where it fits

`setup-sk-skills` is the **run-once setup** for the engineering flow, the precondition everything else assumes rather than a step in the chain. Its neighbours are its readers: triage, which applies the label vocabulary written here; to-spec and to-tickets, which publish into the tracker named here; and wayfinder, which reads the "Wayfinding operations" section of the same tracker file to know how maps and child tickets are stored. The domain-doc layout it records is the one domain-modeling fills in later, and the glossary it seeds is the one domain-modeling sharpens: setup may write `CONTEXT.md` once, from terms you confirmed, and domain-modeling owns it from there, creating ADRs and resolving ambiguities lazily as they come up. For which skill to reach for next, ask-sk routes the whole set.
