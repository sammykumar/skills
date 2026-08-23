# Auto-trigger hook for the design-interview workflow

A `UserPromptSubmit` hook that notices when a prompt is a clear new-feature or design ask and auto-starts the grilling workflow (invoke the `grilling` + `domain-modeling` skills, interview, record the design), so you do not have to remember the slash command. Works on both Claude Code and Codex. Design record: [`docs/plans/2026-08-23-auto-trigger-grill-with-docs.md`](../../../../docs/plans/2026-08-23-auto-trigger-grill-with-docs.md). Rationale for the shape: [`.agents/adr/0003-auto-trigger-injects-sub-skills-not-the-wrapper.md`](../../../../.agents/adr/0003-auto-trigger-injects-sub-skills-not-the-wrapper.md).

## Files

- `detect-new-feature.sh` — Claude Code hook script. Keyword gate, then a `claude -p --model haiku` confirm.
- `detect-new-feature-codex.sh` — Codex mirror. Same logic; confirm via `codex exec`.
- `injected-context.md` — the exact instructions both scripts inject on a confirmed hit. Single source of truth. It never names the user-invoked wrapper skill (naming it would make the model try to invoke a `disable-model-invocation` skill, which the harness blocks).
- `hooks.json` — Claude plugin hook wiring (`${CLAUDE_PLUGIN_ROOT}`-relative).
- `codex-hooks.json` — Codex hook wiring (absolute path; adjust if your checkout moves).

## How it behaves

On every prompt the script: checks a per-session fire-once marker (skip if already fired); runs a keyword gate for feature/design language (skip on miss); asks a fast model to confirm it is genuinely a new-feature ask (skip on NO or if the CLI is missing); on YES, writes the marker and injects `injected-context.md`. It never exits non-zero on a skip path, so it can never block your prompt.

## Requirements

- `jq` on PATH.
- Claude side: the `claude` CLI (for the Haiku confirm).
- Codex side: the `codex` CLI. Set `GRILL_CODEX_MODEL` to a cheap model your account can run; if unset, the confirm uses your configured default Codex model.

## Wiring it up

### Claude Code

Three routes, pick one:

1. **Bundled in a plugin (the eventual home).** Ship the hook in your own Claude Code plugin: either add a `hooks` key to the plugin's `plugin.json` with the contents of `hooks.json`, or place a `hooks/hooks.json` at the plugin root. The `${CLAUDE_PLUGIN_ROOT}`-relative command in `hooks.json` resolves against the installed plugin directory. Note: this repo currently disables the `mattpocock-skills` plugin in its own `.claude/settings.json`, so a plugin-bundled hook will not fire in this repo's own sessions.
2. **User settings (fires everywhere, including this repo).** Add a `hooks.UserPromptSubmit` entry to `~/.claude/settings.json` pointing `command` at the absolute path of `detect-new-feature.sh`.
3. **Project settings (this repo only).** Same entry in this repo's `.claude/settings.json`.

### Codex

Either copy `codex-hooks.json` to `~/.codex/hooks.json` (or `<repo>/.codex/hooks.json` for one project), or add this to `~/.codex/config.toml`:

```toml
[[hooks.UserPromptSubmit]]

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "/Users/samkumar/Development/SK-Productions-LLC/skills/skills/engineering/grill-with-docs/hooks/detect-new-feature-codex.sh"
```

Inspect and trust hooks with the `/hooks` command in Codex. Codex hooks are a newer feature; pin the Codex version you rely on.

## Caveats

- The `UserPromptSubmit` hook is globally scoped: it fires for every prompt in a session where it is registered, in any repo.
- Fire-once is per session (keyed by `session_id`, marker in `$TMPDIR`). It does not coordinate with a manual run of the slash command in the same session.
- The Claude confirm runs inside the 30s `UserPromptSubmit` timeout; a hang drops the injection silently.
- The confirm calls a coding-agent CLI from inside that agent's own hook. It runs as a separate process and is fine in practice, but it adds latency and a model call on every keyword-candidate prompt.
- The scripts avoid here-docs-inside-`$()` and embedded apostrophes because macOS system bash (3.2) mis-parses that combination.
