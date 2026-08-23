# Auto-trigger grill-with-docs on new-feature sessions

Status: implemented (scripts + config, tested); plugin bundling deferred as a follow-up. Last updated 2026-08-23.

## Implementation

Lives in `skills/engineering/grill-with-docs/hooks/` (co-located with the skill it serves; no new top-level folder):

- `detect-new-feature.sh` (Claude) and `detect-new-feature-codex.sh` (Codex): keyword gate then per-harness model confirm (`claude -p --model haiku` / `codex exec`), fire-once per `session_id`, never exits non-zero on a skip path.
- `injected-context.md`: the shared injected instruction (invoke `grilling` + `domain-modeling`, inlined plan-location rules); never names the wrapper.
- `hooks.json` (Claude, `${CLAUDE_PLUGIN_ROOT}`-relative), `codex-hooks.json` (Codex), `README.md` (wiring for both platforms + the deferred plugin/local-dev routes).

Verified: `bash -n` clean; a malicious prompt with `$(...)`/backticks does not inject (value is not re-expanded); fire-once, gate-miss, and model-NO all stay silent with exit 0; emitted JSON is well-formed; the real Haiku confirm fires on "add a CSV export feature" and correctly declines a typo-fix that merely contains "implement". Found and fixed along the way: macOS system bash (3.2) mis-parses a here-doc nested in `$()` with an embedded apostrophe, so the confirm prompt is a plain double-quoted string and the gate drops the `let's` apostrophe alternative.

## Problem

`grill-with-docs` is a user-invoked skill reached only via `/grill-with-docs`. Sam wants it to fire automatically whenever a session is "about a new feature," because he forgets to type the slash command. It has to work on both Claude Code and Codex.

## The load-bearing constraint (verified)

A hook cannot execute a slash command or invoke a skill on either platform. This is the ceiling the whole design lives under.

- **Claude Code:** "Command hooks communicate through stdout, stderr, and exit codes only. They can't trigger `/` commands or tool calls." The only lever is a `UserPromptSubmit` (or `SessionStart`) hook returning `additionalContext`, which is injected into the model's context; the model then decides whether to act. Source: code.claude.com/docs/en/hooks-guide.md (Limitations), hooks.md.
- **Codex CLI:** now has an equivalent hooks system with the same event names (`UserPromptSubmit`, `SessionStart`, ...), configured via `hooks.json` or `[hooks]` in `config.toml`. `UserPromptSubmit` receives the prompt text on stdin and can return `additionalContext`. `notify` is the wrong tool (fires post-turn, outbound-only, cannot inject). Source: learn.chatgpt.com/docs/hooks, openai/codex docs.

So "auto-start" is not a hard guarantee. It is: the hook classifies the prompt, and on a match injects strong instructions that the model then complies with. This is disclosed because Sam chose "auto-start immediately" before knowing hooks cannot literally start a skill.

## The disable-model-invocation trap (verified)

`grill-with-docs` has `disable-model-invocation: true` (it is user-invoked by repo convention). This is a hard block: the model can never call it, and if a hook injects "invoke grill-with-docs," Claude Code blocks the call and tells the model not to reproduce the steps another way, poisoning the turn.

Resolution (recorded in `.agents/adr/0003-auto-trigger-injects-sub-skills-not-the-wrapper.md`): the injected context must **never name `grill-with-docs`**. Instead it names the two underlying skills, `grilling` and `domain-modeling` (both verified model-invocable, no `disable-model-invocation`), and carries the "record the design per the repo's plan convention" instruction inline. The user-invoked wrapper is left untouched for manual use; the hook is a parallel auto-entry into the same workflow.

## Decisions settled so far

- **Behavior on detection:** auto-start the grilling interview immediately, no confirmation step. (Sam's call; accepts that a false positive drops him straight into a grilling. Softened only by the ceiling above: it is strong injection plus model compliance, not a forced start.)
- **Detection sensitivity:** fire only on clear feature/design asks (build X, design Y, how should we build Z). Skip bug fixes, questions, small edits.
- **Mechanism, both platforms:** a `UserPromptSubmit` hook that classifies the prompt text and, on a match, injects `additionalContext` instructing the model to invoke `grilling` + `domain-modeling` and record the design. Symmetric across Claude Code and Codex.
- **Claude injection format:** nest `additionalContext` under `hookSpecificOutput` (top-level is silently ignored); 10,000-char output cap; `UserPromptSubmit` hooks have a 30s timeout (bounds classifier cost).
- **Classifier:** hybrid. A keyword/regex gate runs on every prompt; only on a hit does it call a fast Haiku classifier to confirm before injecting. Cost falls only on candidate prompts, and the confirm step must finish inside the 30s timeout (a hang drops the injection).
- **Re-fire suppression:** the hook writes a marker keyed by `session_id` on first injection; later prompts in that session skip. Fire once per session.
- **Claude delivery:** bundle the hook in a Claude Code plugin (`hooks/hooks.json`, script referenced via `${CLAUDE_PLUGIN_ROOT}`). Sam is publishing his own fork as his own plugin; **creating that plugin is a separate follow-up feature**, so this design produces the hook script + `hooks/hooks.json` ready to bundle, and the plugin-manifest wiring lands with the follow-up. Local caveat still holds: with the plugin disabled in this repo's `.claude/settings.json`, the bundled hook will not fire in local sessions here.

- **Codex delivery:** a Codex `UserPromptSubmit` hook (`config.toml` `[hooks]` or `hooks.json`) running the same classify-and-inject logic, symmetric with Claude. Pin the Codex version it depends on.
- **Confirm backend:** per-harness. The Claude hook confirms with `claude -p --model haiku`; the Codex hook confirms with its own native model call (`codex exec` with a cheap model). Shared keyword-gate logic in spirit, but two scripts.
- **Injected context:** self-contained and inline. It spells out the workflow (invoke `grilling` + `domain-modeling`, then record the design per the repo's plan convention) and never names `grill-with-docs`. Accepts that it duplicates the wrapper's body and must be re-synced by hand if the wrapper changes.

## Resolved mechanism (both platforms)

A `UserPromptSubmit` hook, on every prompt:

1. Reads the prompt (and `session_id`) from stdin.
2. Checks a session-keyed marker; if this session already fired, exits quietly (no output).
3. Runs a keyword/regex gate for clear feature/design asks. No match, exit quietly.
4. On a keyword hit, calls the harness-native fast model to confirm it is genuinely a new-feature ask, inside the 30s timeout. Not confirmed, exit quietly.
5. On confirmation, writes the session marker and returns `additionalContext` (Claude: nested under `hookSpecificOutput`, under 10,000 chars) carrying the self-contained instruction to begin the grilling workflow: invoke `grilling` and `domain-modeling`, interview before implementing, and record the design per the repo's plan convention. Never names `grill-with-docs`.

## Tasks

1. [done] Keyword-gate + confirm classifier logic (Claude `claude -p --model haiku`; Codex `codex exec`).
2. [done] Self-contained injected-context string with inlined plan-location rules; never names the wrapper. Under 10,000 chars.
3. [done] Session-keyed fire-once marker.
4. [done] `hooks.json` (Claude) via `${CLAUDE_PLUGIN_ROOT}`.
5. [done] Codex wiring (`codex-hooks.json` + a `[[hooks.UserPromptSubmit]]` config.toml snippet in README).
6. [follow-up] Create Sam's own Claude Code plugin and bundle the hook (add a `hooks` key to its `plugin.json` or a `hooks/hooks.json` at plugin root). The scripts are authored and ready; only the plugin manifest wiring remains.
7. [deferred] Registration: Sam chose to leave both the Claude and Codex hooks unwired for now and register them as part of the plugin follow-up. Nothing fires yet; the scripts sit ready. README documents all routes (user settings, project settings, plugin bundle; Codex `hooks.json` or `config.toml`).

## Caveats to carry into implementation

- Never name `grill-with-docs` in injected context (see trap above).
- Codex hooks are a new feature; pin the Codex version the hook depends on.
- Plugin-bundled hooks stop firing the moment the plugin is disabled; no persistent effect.
- Verify calling `claude -p` from inside a Claude `UserPromptSubmit` hook is safe (nested non-interactive session) and stays within the 30s timeout and acceptable per-prompt cost.
- Fire-once marker only suppresses hook re-fire; it does not coordinate with a manual `/grill-with-docs` run in the same session (minor, accepted).

## Caveats to carry into implementation

- Never name `grill-with-docs` in injected context (see trap above).
- Codex hooks are a new feature; pin the Codex version the hook depends on.
- Plugin-bundled hooks stop firing the moment the plugin is disabled; no persistent effect.
