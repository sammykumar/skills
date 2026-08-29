# Mine User vocab from past sessions during `/setup-sk-skills`

Onboarding a repo currently leaves the glossary empty: `CONTEXT.md` is created lazily, one term at a time, by `domain-modeling`. But by the time a repo gets onboarded there are usually dozens of past agent sessions in which the user has already been naming things. That language is sitting on disk and nobody reads it. This adds a fourth section to `setup-sk-skills` that mines it and proposes terms.

## Resolved design

### Ownership: fully inside `setup-sk-skills`

The step lives in `setup-sk-skills` and writes accepted terms into `CONTEXT.md` itself.

_Why:_ the alternative was to keep `domain-modeling` as the only writer of the glossary. That invariant exists to stop machine-generated glossaries nobody re-reads, and confirmation-before-write preserves the spirit of it: nothing lands in `CONTEXT.md` that the user did not accept. The payoff is that a single onboarding run leaves a repo with a real glossary instead of an empty one.

### Sessions read: this repo plus its worktrees

Claude Code writes one JSONL per session under `~/.claude/projects/<cwd-slug>/`, where the slug is the working directory with separators replaced. Each git worktree therefore gets its own slug (`...-skills` vs `...--worktrees-<name>`), so an exact-slug match would miss most of the history on a machine that uses worktrees. The miner derives the slug from `$PWD` at run time and prefix-matches.

Codex writes flat, date-foldered rollouts under `~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl` with no slug at all; the repo is recorded in the `session_meta` record's `payload.cwd`. The miner matches those by cwd prefix instead.

_Verified:_ both layouts and both record shapes were read off disk during design.

### What counts as User vocab: typed turns only, filtered

Only user-role messages, and not all of those. Both harnesses inject text into the user turn that the user never typed:

- Claude Code inlines the whole body of a slash command (a `/ship` invocation appears as a multi-kilobyte user message), plus `system-reminder` blocks and local command stdout.
- Codex inlines `AGENTS.md` instruction blobs and environment context.

The extractor drops those, along with tool results, and keeps what is left.

### Extraction: script pre-pass, model reads only the shortlist

A Node script, `mine-vocab.mjs`, shipped inside the skill folder so it travels with the plugin. Node, not bash + jq: it must parse two different record shapes, and jq is not guaranteed present on a user's machine. It reads newest-session-first, stops at a cap (sessions and total bytes), and reports what it skipped rather than silently truncating.

_Why a script at all:_ this repo alone has 13 MB of transcripts across 10 sessions. Raw transcripts cannot enter context, and an ad-hoc grep would vary run to run.

Ranking: multi-word noun phrases scored by frequency, weighted by how many distinct sessions they appear in (a phrase used once in one long session is jargon of the moment; one used across five sessions is real), and boosted when the phrase also appears in the repo's code or docs, since those are grounded domain nouns. Output is stdout only: a ranked shortlist with a few evidence quotes per entry. Nothing is written to disk, so no mined-transcript artifact can leak into a commit.

### Presentation: ranked table, batch confirm

The model presents one table (term, session spread, one evidence quote, proposed one-line definition) and the user selects which to keep. Kept terms are written into `CONTEXT.md` in its existing format.

Beyond bare terms, the miner also proposes `_Avoid_` lines: near-synonyms the user has been using interchangeably across sessions, with the dominant one proposed as the term and the rest as avoids. This is the thing transcripts know that the codebase does not, and it is the main reason the feature is worth building.

### Placement and re-runs

A new **Section D** after Domain docs, gated on one opt-in question that states how many matching sessions were found. Skipping costs a word, and a fresh repo with no history never burns time on it.

On a repo that already has a `CONTEXT.md`, the miner reads it first and drops candidates already defined (or already listed under an `_Avoid_`). Re-running setup is safe and purely additive.

### Codex parity

The Codex variant does the same thing against Codex's own rollouts; the single script handles both sources. `agents/openai.yaml` stays in sync with `SKILL.md` rather than diverging or no-oping.

## Vocabulary added

`CONTEXT.md` gained **Session transcript** and **User vocab**. A single proposed item is just a *term*: unaccepted until the user confirms it.

## Tasks

1. `mine-vocab.mjs` in the skill folder: locate sessions for both harnesses from `$PWD`, extract typed turns, filter injected text, rank phrases, print the shortlist and what was skipped.
2. Section D in `SKILL.md`: the opt-in question, running the script, the confirmation table, writing accepted terms into `CONTEXT.md`.
3. Section 1 (Explore) gains a session count, so the opt-in question can state it.
4. `agents/openai.yaml` kept in sync.
5. `docs/engineering/setup-sk-skills.md` re-synced per `.agents/writing-docs.md`.
6. `ask-sk` checked: `setup-sk-skills` is already routed, so only its description needs to stay accurate.
7. Changeset.
