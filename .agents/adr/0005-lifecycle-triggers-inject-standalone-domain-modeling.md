# Lifecycle triggers inject standalone domain-modeling via SessionStart and PostToolUse-exit2

To keep the domain model from going stale, two lifecycle hooks nudge `domain-modeling` on their own: a `SessionStart` hook on a new repo (no `CONTEXT.md` and under 10 commits) and a `PostToolUse` hook when an edit touches `CLAUDE.md`, `AGENTS.md`, or `agents/*.yaml`. Both fire directly with no model-confirm gate and inject `domain-modeling` standalone, without the `grilling` interview, because a full design grilling on every instruction edit or fresh session would be obnoxious.

The surprising part, worth recording so nobody "fixes" it: the instruction-edit trigger delivers its nudge differently per harness. On Codex, `PostToolUse` supports `additionalContext` and we use it. On Claude Code, `additionalContext` is not documented as honored on `PostToolUse` (verified against the raw hooks reference on 2026-08-23), so the nudge is delivered as exit-2 stderr instead. A reader seeing exit-2 stderr where the sibling `SessionStart` hook uses clean `additionalContext` would assume it is a mistake; it is not. The purpose-built `FileChanged` and `InstructionsLoaded` events were rejected because injection on them is unverified.

## Considered options

- **Use `additionalContext` uniformly on both triggers and both harnesses.** Rejected: not honored on `PostToolUse` in Claude Code, so the instruction-edit nudge would silently never reach the model there.
- **Bundle `grilling` with the lifecycle nudge, like the new-feature hook does.** Rejected: a relentless design interview on every `CLAUDE.md` edit or new session is the wrong altitude; these moments want a quiet glossary check, not a grilling.
- **React to instruction edits via `FileChanged` / `InstructionsLoaded`.** Rejected: those events fit semantically but their context injection is unverified in the docs.

## Consequences

The instruction-edit nudge on Claude Code is exit-2 stderr feedback, which is nudge-grade rather than formal context injection: acceptable, since a hook can never force a skill to run anyway. The two triggers cross-suppress against the existing `grill-with-docs` session marker so a session that already started the grilling workflow is not double-nudged. Like ADR 0003, the injected text never names the `grill-with-docs` wrapper.
