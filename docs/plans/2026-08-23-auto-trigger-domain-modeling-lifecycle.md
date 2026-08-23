# Auto-trigger domain-modeling at lifecycle moments

Status: implemented (scripts authored + tested; Claude wired locally for dogfood, Codex authored but unwired). Plugin bundling deferred. Last updated 2026-08-23.

## Problem

The `domain-modeling` skill is model-invocable but nobody remembers to reach for it. Sam wants it to fire on its own at the moments a project's domain model is most likely going stale or missing: a brand-new repo, and an edit to the agent-instruction files. This is deliberately different from the existing `grill-with-docs` auto-trigger, which is prompt-triggered ("this prompt sounds like a new feature"). This feature is event/lifecycle-triggered ("the domain model probably needs attention right now").

The existing new-feature hook already injects `domain-modeling` (bundled with `grilling`) on new-feature and refactor prompts, so those moments are covered. This feature adds the two genuinely new lifecycle triggers and injects `domain-modeling` standalone, without launching a relentless grilling interview.

## The load-bearing constraint (carried from grill-with-docs, still true)

A hook cannot invoke a skill on either harness. Its only lever is injecting context the model then chooses to act on. So "auto-trigger" is a strong nudge plus model compliance, never a forced run. This is the ceiling the whole design lives under, same as the existing hook.

## Verified harness facts (fact-find, 2026-08-23)

Confirmed against the raw Claude Code hooks reference (`code.claude.com/docs/en/hooks.md`) and Codex hooks docs (`learn.chatgpt.com/docs/hooks`):

- `SessionStart` context injection via `additionalContext` is verified on both Claude Code and Codex. The new-repo trigger uses it directly.
- `PostToolUse` matching a tool name and a file path is verified on Claude Code: `matcher: "Edit|Write"` plus `if: "Edit(CLAUDE.md)"` fires only when those tools touch that file.
- `PostToolUse` + `additionalContext` is documented as honored on Codex, but NOT on Claude Code. On Claude Code the documented channels to get text in front of the model from `PostToolUse` are exit-2 stderr ("shows stderr to Claude") or `decision:"block"` + `reason` (with `continueOnBlock:true`). The purpose-built `FileChanged` and `InstructionsLoaded` events exist but injection on them is unverified, so they are not used.

## Design

Two triggers. Both fire directly (no model-confirm gate). Both inject standalone `domain-modeling` (never `grilling`, never the `grill-with-docs` wrapper name, per ADR 0003's block-trap rule).

### Trigger 1: new repo (`SessionStart`)

- Sources: fire on `startup` and `clear` only; skip `resume` and post-compact re-injections so work in progress is not re-nudged.
- Fires when both hold: no `CONTEXT.md` and no `CONTEXT-MAP.md` at the repo root, AND `git rev-list --count HEAD` is under 10.
- Delivery: `additionalContext` nested under `hookSpecificOutput` (verified on both harnesses).
- Injected message (new-repo copy): establish vocabulary early, invoke `domain-modeling`, create `CONTEXT.md` as the first terms crystallize. Keep it a glossary only.

### Trigger 2: instruction edit (`PostToolUse`)

- Matcher `Edit|Write`, with `if` clauses scoping to `CLAUDE.md`, `AGENTS.md`, and `agents/*.yaml`. Deliberately excludes `CONTEXT.md` itself: editing the glossary must not trigger a glossary review (a loop).
- Delivery is asymmetric by harness because of the verified-facts split above:
  - Claude Code: exit-2 stderr carrying the nudge text.
  - Codex: `PostToolUse` `additionalContext`.
- Injected message (instruction-edit copy): the agent instructions just changed, invoke `domain-modeling` and reconcile the glossary and domain model with them.

### Shared policy

- Fire once per session per trigger type. Each trigger writes its own session-keyed marker under `${TMPDIR:-/tmp}`.
- Cross-suppress: before firing, check for the existing `grill-with-docs` marker (`${TMPDIR:-/tmp}/grill-with-docs.${SID}.fired`). If the grilling hook already fired this session, skip the lifecycle nudge, since `domain-modeling` is already in play.
- Never exit non-zero on a no-op path for `SessionStart`/`UserPromptSubmit`-shaped events. The instruction-edit trigger's deliberate exit-2 on Claude Code is the one intentional non-zero, and only on a confirmed match.

### Harness coverage for v1

Author both Claude Code and Codex scripts. Wire only Claude Code, in this repo's project settings (`.claude/settings.json`), so the feature actually fires here and Sam can dogfood it. The Codex scripts sit ready-but-unwired, matching the existing hook's pattern. Full plugin bundling stays a separate follow-up.

### Code home

`skills/engineering/domain-modeling/hooks/`, co-located under the skill it serves, mirroring how `grill-with-docs` co-located its hook. Reuse the existing machinery directly: stdin to `jq` parse, the session-keyed marker, and the `jq -n --rawfile` injection shape. The per-trigger injected messages live as their own files (new-repo copy, instruction-edit copy), the way `injected-context.md` does for the existing hook.

## Accepted trade-offs

- Dogfooding the instruction-edit trigger in this very repo means editing `CLAUDE.md` here nudges once per session. Acceptable, capped by the marker.
- The under-10-commits gate can nudge a near-empty new repo with little to model yet. The new-repo copy softens this ("as terms crystallize"), and the model can decline when there is nothing to name.
- The instruction-edit nudge reaches the Claude Code model as exit-2 stderr feedback, not formal context injection. Nudge-grade reliability, which is all the ceiling allows anyway.

## Tasks

1. [done] New-repo `SessionStart` script (`detect-new-repo.sh`, shared by both harnesses): source filter (skip resume/compact), no-CONTEXT + under-10-commits gate, marker, `additionalContext` injection.
2. [done] Instruction-edit `PostToolUse` scripts: Claude Code (`detect-instruction-edit.sh`, exit-2 stderr) and Codex (`detect-instruction-edit-codex.sh`, `additionalContext`). File-set filtering done in-script (basename CLAUDE.md/AGENTS.md, or `*/agents/*.yaml`), CONTEXT.md excluded.
3. [done] Two injected-message files (`new-repo-context.md`, `instruction-edit-context.md`). Neither names `grill-with-docs` (verified by test).
4. [done] Cross-suppress check against the `grill-with-docs.${SID}.fired` marker; per-trigger-type markers (`domain-modeling-newrepo.*`, `domain-modeling-instredit.*`).
5. [done] Claude wiring in this repo's `.claude/settings.json` for dogfood (gitignored, so local-only and not committed; correct because commands use machine-specific absolute paths). Codex `codex-hooks.json` authored but unwired.
6. [done] `hooks/README.md` documenting both harnesses and the wiring routes, matching the grill-with-docs hooks README.
7. [done] ADR `.agents/adr/0005-lifecycle-triggers-inject-standalone-domain-modeling.md` recording the mechanism choices.

Verified: `bash -n` clean on all three scripts; both JSON manifests and `.claude/settings.json` parse; new-repo fires on a young no-CONTEXT repo and stands down on mature repos, CONTEXT-present repos, non-git dirs, `resume` source, an existing fire marker, and the grill marker; instruction-edit fires (Claude exit-2 with the nudge on stderr; Codex valid `additionalContext` JSON) on CLAUDE.md/AGENTS.md/`agents/*.yaml`, and stands down on CONTEXT.md, non-agents yaml, non-edit tools, a fire marker, and the grill marker. Output JSON validated with a strict parser.

## Deferred

- Plugin bundling and Codex registration (rides the same follow-up the grill-with-docs hook is waiting on).
- The two fuzzy prompt-shaped triggers Sam originally floated (major refactor, new functionality) stay with the existing new-feature prompt hook; not rebuilt here.
