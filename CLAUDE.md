# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of agent **skills** (each a folder with a `SKILL.md`) shipped two ways: as the `sk-skills` Claude Code plugin (`.claude-plugin/plugin.json`) and as editable Agent Skills via skills.sh. There is no application to build or run: the "source" is Markdown instructions plus a small amount of glue (bash scripts, two Node scripts, and a test suite over the one that carries real logic). Every skill is dual-harness, carrying both a `SKILL.md` (Claude Code) and an `agents/openai.yaml` (Codex) that must stay in sync. `CONTEXT.md` holds the domain vocabulary (Issue tracker, Issue, Decision ticket, Triage role); read it before naming things. The `.agents/` folder holds the authoring docs referenced throughout this file (`invocation.md`, `writing-docs.md`, `install-block.md`, `adr/`).

This is a fork of https://github.com/mattpocock/skills, kept for local customization.

## Commands

- `claude plugin validate . --strict` — run after editing `.claude-plugin/plugin.json` or `marketplace.json`.
- `npm run check-plugin-version` — asserts `plugin.json` version matches `package.json`; run after either changes.
- `npm test` — runs Node's built-in test runner over `skills/**/*.test.mjs`; run after editing any skill's `.mjs` glue.
- `scripts/list-skills.sh` — list every `SKILL.md` path in the repo.
- `scripts/link-skills.sh` — symlink every skill into `~/.claude/skills` and `~/.agents/skills` for local use; re-run after adding, removing, or renaming a skill. Dev-only, not an installer.
- `scripts/scaffold-ship.sh /path/to/repo [branch]` — cut a repo's `/ship` command from the canonical template into its `.claude/commands/ship.md`. See below.

### The `/ship` command (per-repo, from a template)

`/ship` is a project-local Claude Code command, not a plugin-distributed one: each repo carries its own `.claude/commands/ship.md`, tuned to that repo's real gates and deploy story. The plugin does not ship it. `.agents/ship-template.md` is the canonical source they are cut from: it holds the invariant spine (commit discipline, the attribution rules, branch-from-`origin` never HEAD, merge-not-squash, verify-don't-infer, honest report) as fixed prose, with two `REPO:` fill-in zones (`GATES`, `DEPLOY`) and a `{{DEFAULT_BRANCH}}` token. To stand one up in another repo, run `scripts/scaffold-ship.sh /path/to/repo [branch]`, then fill the two zones. When you improve the spine, edit the template; the per-repo copies are instances, so re-cut or hand-patch them to match.

### Release flow (changesets)

- `npm run changeset` — add a changeset describing any user-facing skill change.
- `npm run version` — applies changesets and runs `sync-plugin-version.mjs` to copy `package.json`'s version into `plugin.json`. Do not hand-edit either version.

## Skill authoring conventions

Skills are organized into bucket folders under `skills/`:

- `engineering/`: daily code work
- `productivity/`: daily non-code workflow tools
- `misc/`: kept around but rarely used, not promoted
- `in-progress/`: beta: public on purpose, feedback wanted, not shipped in the plugin
- `deprecated/`: no longer used

Every skill in `engineering/` or `productivity/` (the **promoted** buckets) must have a reference in the top-level `README.md` and an entry in `.claude-plugin/plugin.json`'s `skills` array (the Claude Code plugin ships exactly the promoted set). Skills in `misc/`, `in-progress/`, and `deprecated/` must not appear in either.

Install commands are copied verbatim from [.agents/install-block.md](./.agents/install-block.md). `.claude-plugin/marketplace.json` makes the repo its own single-plugin marketplace (a fallback the install block explains, not the documented route). Run `claude plugin validate . --strict` after touching either manifest. Why a Claude plugin but not (yet) a Codex one lives in [.agents/adr/0002-ship-as-a-claude-code-plugin.md](./.agents/adr/0002-ship-as-a-claude-code-plugin.md).

Each skill entry in the top-level `README.md` must link the skill name to its `SKILL.md`.

Each bucket folder has a `README.md` that lists every skill in the bucket with a one-line description, with the skill name linked to its `SKILL.md`. The promoted buckets' `README.md`s and the top-level `README.md` group entries into **User-invoked** and **Model-invoked**; non-promoted bucket `README.md`s (`misc/`, `in-progress/`) use a flat list.

Skills in `engineering/` and `productivity/` also have a human-facing docs page at `docs/<bucket>/<skill-name>.md` (the docs tree mirrors those two bucket folders under `skills/`). These are in-repo docs pages: the docs path is repo organisation only. When you add, rename, or change the behaviour of a skill in `engineering/` or `productivity/`, create or re-sync its docs page following [.agents/writing-docs.md](./.agents/writing-docs.md). A finished page carries four sections: **What it does**, **When to reach for it**, **Common questions**, and **It's working if**. `writing-docs.md` holds the template, the section order, and where to hunt for the questions. Skills in the non-promoted buckets (`misc/`, `in-progress/`, `deprecated/`) get **no** docs page.

Every `SKILL.md` is either user-invoked (`disable-model-invocation: true` plus `policy.allow_implicit_invocation: false` in `agents/openai.yaml`, reachable only by the human) or model-invoked (model- or user-reachable). See [.agents/invocation.md](./.agents/invocation.md).

[`ask-sk`](./skills/engineering/ask-sk/SKILL.md) is the router that maps every user-reachable skill and how they relate. The same trigger that re-syncs a docs page applies to it: whenever you add, rename, remove, or change how a user-reachable skill fits the flows, re-read `ask-sk`'s `SKILL.md` and update it so the map stays accurate: a new skill it never mentions, or a stale one it still routes to, is a router that lies.

To (re)link every skill into the local harness skill directories (`~/.claude/skills`, `~/.agents/skills`), run `scripts/link-skills.sh`. Each entry is a symlink into this repo, so a `git pull` keeps installed skills current; re-run the script after adding, removing, or renaming a skill.

No em-dashes anywhere in this repo's prose (`SKILL.md` files, docs, `README.md`, `CHANGELOG.md`, ADRs, changesets, code comments). Where a sentence reaches for one, rewrite it instead with a comma, colon, period, parentheses, or a conjunction, whichever the sentence actually wants; never do a blind character substitution.

## Agent skills

### Issue tracker

Issues and specs live as markdown files under `docs/issues/`, kept separate from the flat design records in `docs/plans/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical role names, used verbatim. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at the root, ADRs in `.agents/adr/`. See `docs/agents/domain.md`.
