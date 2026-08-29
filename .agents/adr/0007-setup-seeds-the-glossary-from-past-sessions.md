# `setup-sk-skills` seeds `CONTEXT.md` from past sessions

Until now, `setup-sk-skills` wrote configuration and nothing else: `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, `docs/agents/triage-labels.md`, and an `## Agent skills` block. Glossary content was `domain-modeling`'s alone, created lazily, one term at a time, when a term actually got resolved in conversation. `docs/agents/domain.md` says so in as many words: if `CONTEXT.md` doesn't exist, proceed silently, don't suggest creating it.

`setup-sk-skills` now also mines past session transcripts and writes accepted terms into `CONTEXT.md`. This ADR records why that exception was made and what keeps it honest.

## The problem

A repo is usually onboarded late. By the time anyone types `/setup-sk-skills`, dozens of agent sessions have already happened in that working directory, and across all of them the user has been naming things: the stuck lead sweeper, the lead profile drawer, the plugin marketplace. That is the project's real vocabulary, it is sitting on disk in `~/.claude/projects/` and `~/.codex/sessions/`, and nothing reads it.

Lazy creation means the glossary only ever captures terms that come up again *after* setup. Vocabulary settled two months ago in a conversation nobody will revisit stays uncaptured, and every skill that reads `CONTEXT.md` for its vocabulary keeps drifting to synonyms.

## Decision

Add a **Section D** to `setup-sk-skills` that mines the transcripts and proposes terms, and let that section write the accepted ones into `CONTEXT.md`.

The guardrails that keep the lazy-glossary rule's intent intact:

- **Nothing is written without confirmation.** The miner produces candidates; the user picks. A machine-generated glossary is exactly the artifact nobody re-reads, and confirmation is what stops this from becoming one.
- **The step is opt-in**, gated on a single question that states how many sessions were found. On a repo with no history it never runs.
- **Terms already in the glossary are filtered before the user ever sees them**, including anything listed under an `_Avoid_`. Re-running setup is additive, never a re-litigation.
- **Nothing is written to disk by the miner itself.** The shortlist goes to stdout and dies with the process, so pasted secrets and other people's names in old transcripts cannot land in a commit.
- **`domain-modeling` still owns the glossary from there on.** Setup seeds; sharpening, `_Avoid_` curation, and ambiguity resolution stay where they were.

## Alternatives considered

- **Put the step in `domain-modeling` instead.** Preserves the invariant exactly and makes mining available any time, not just at onboarding. Rejected because the payoff is highest precisely at onboarding: the whole point is that a repo arrives with history and leaves setup with a glossary, rather than with an empty file and a promise.
- **Auto-write everything mined and let the user prune.** Rejected: the ranking is a heuristic over n-grams and cannot tell a domain noun from an automation's phrasing. Unreviewed output would poison the one file every other skill trusts.
- **A separate `vocab-candidates.md` for `domain-modeling` to draw from later.** Rejected as a file nobody opens, and a second place where vocabulary lives.

## What this creates

- `CONTEXT.md` is now written by two skills. `setup-sk-skills` may seed it once, at onboarding, with confirmed terms; `domain-modeling` owns it thereafter. If a third writer is ever proposed, this is the boundary to argue against.
- The miner is the repo's first piece of real logic, so the repo now has tests: `npm test` runs Node's built-in runner over `skills/**/*.test.mjs`. Adding a test runner was a deliberate one-time call, not an invitation to grow a framework.
- Transcript formats are external and unversioned. Both harnesses inject text into the user role (slash-command bodies, task notifications, `AGENTS.md` blobs, compaction preambles), and the filters that strip them are the part most likely to go stale. When a shortlist fills up with harness prose, that filter list is where to look.
