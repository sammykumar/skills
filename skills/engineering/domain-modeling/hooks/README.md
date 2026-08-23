# Lifecycle auto-trigger hooks for domain-modeling

Two hooks that nudge the model to run the `domain-modeling` skill standalone (no grilling) at the moments a project's domain model is most likely stale or missing. You do not have to remember to reach for the skill. Design record: [`docs/plans/2026-08-23-auto-trigger-domain-modeling-lifecycle.md`](../../../../docs/plans/2026-08-23-auto-trigger-domain-modeling-lifecycle.md). Rationale for the mechanism split: [`.agents/adr/0005-lifecycle-triggers-inject-standalone-domain-modeling.md`](../../../../.agents/adr/0005-lifecycle-triggers-inject-standalone-domain-modeling.md).

These never name the user-invoked `grill-with-docs` wrapper (naming a `disable-model-invocation` skill makes the harness block the call). They inject `domain-modeling` directly, which is model-invocable.

## The two triggers

- **New repo** (`SessionStart`): fires on a fresh session when the repo has no `CONTEXT.md` / `CONTEXT-MAP.md` at its root and fewer than 10 commits. Nudges the model to plant a glossary early.
- **Instruction edit** (`PostToolUse`): fires when an `Edit`/`Write` touches `CLAUDE.md`, `AGENTS.md`, or a skill's `agents/*.yaml`. Nudges the model to reconcile the glossary with the changed instructions. `CONTEXT.md` is deliberately excluded so editing the glossary does not trigger a glossary review.

Both fire directly (no model-confirm gate), once per session per trigger type, and stand down if the `grill-with-docs` hook already fired this session (checked via its `${TMPDIR}/grill-with-docs.${SID}.fired` marker), since that workflow already puts `domain-modeling` in play.

## Files

- `detect-new-repo.sh`: shared `SessionStart` script for both harnesses (`SessionStart` additionalContext injection is verified on both).
- `detect-instruction-edit.sh`: Claude Code `PostToolUse` script. Delivers via **exit-2 stderr**, because Claude Code does not honor `additionalContext` on `PostToolUse`.
- `detect-instruction-edit-codex.sh`: Codex `PostToolUse` script. Delivers via `additionalContext` (honored on Codex). Codex's tool_input shape for edits is unverified; confirm the field names when wiring.
- `new-repo-context.md`, `instruction-edit-context.md`: the exact per-trigger text each script injects. Single source of truth.
- `hooks.json`: Claude plugin hook wiring (`${CLAUDE_PLUGIN_ROOT}`-relative).
- `codex-hooks.json`: Codex hook wiring (absolute paths; adjust if your checkout moves).

## Requirements

- `jq` on PATH. No model CLI is needed (these fire directly, unlike the grill-with-docs hook).

## Wiring it up

### Claude Code

Currently wired for dogfood in this repo's `.claude/settings.json` (project settings, absolute paths). Other routes:

1. **Bundled in a plugin (the eventual home).** Ship the hook in the plugin: add a `hooks` key to `plugin.json` or place a `hooks/hooks.json` at the plugin root, using the `${CLAUDE_PLUGIN_ROOT}`-relative commands from `hooks.json`. Note: this repo disables the `sk-skills` plugin in its own `.claude/settings.json`, so a plugin-bundled hook would not fire in this repo's own sessions (which is why the local dogfood route uses project settings directly).
2. **User settings (fires everywhere).** Add the same `SessionStart` and `PostToolUse` entries to `~/.claude/settings.json` with absolute paths.

### Codex

Not wired yet (author-both, wire-Claude-only for v1). When ready: copy `codex-hooks.json` to `~/.codex/hooks.json` (or `<repo>/.codex/hooks.json`), or add the equivalent `[[hooks.SessionStart]]` / `[[hooks.PostToolUse]]` blocks to `~/.codex/config.toml`. Verify the Codex `PostToolUse` tool_input field names against a real edit first. Codex hooks are a newer feature; pin the version you rely on.

## Caveats

- The instruction-edit nudge on Claude Code is exit-2 stderr feedback, which is nudge-grade, not formal context injection. That is all the "a hook cannot invoke a skill" ceiling allows anyway.
- Dogfooding in this repo means editing `CLAUDE.md`, `AGENTS.md`, or an `agents/*.yaml` here nudges once per session. Accepted, capped by the marker.
- The `< 10 commits` gate can nudge a near-empty new repo; the new-repo copy softens this ("ignore if there is not yet enough of a domain to model").
- Fire-once is per session per trigger type (markers in `$TMPDIR`, keyed by `session_id`). It does not coordinate with a manual run of the skill or the slash command in the same session.
- The scripts avoid here-docs-inside-`$()` and embedded apostrophes because macOS system bash (3.2) mis-parses that combination.
