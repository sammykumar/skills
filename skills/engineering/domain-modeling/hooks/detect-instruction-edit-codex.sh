#!/usr/bin/env bash
# PostToolUse hook (Codex CLI): Codex-side mirror of detect-instruction-edit.sh.
# When an edit touches this repo's agent-instruction files (CLAUDE.md, AGENTS.md,
# agents/*.yaml) nudge the model to reconcile the domain glossary via the
# `domain-modeling` skill. Standalone: no grilling.
#
# Codex DOES honor additionalContext on PostToolUse, so unlike the Claude script
# this injects context rather than using exit-2 stderr. Codex's tool_input shape
# for edits is not verified (Codex edits via its own patch tooling), so the file
# path is read from several likely fields and the tool-name gate is intentionally
# loose. Confirm the field names when you actually wire this on Codex.
# Fires once per session for this trigger type; stands down if the grill-with-docs
# hook already fired. Never names that wrapper. See README.md.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECT_FILE="$HOOK_DIR/instruction-edit-context.md"

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
SID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // .tool_input.arguments.file_path // empty')"
SID="${SID:-$PPID}"

[ -n "$FILE" ] || exit 0

# Which files count as agent instructions. CONTEXT.md is deliberately excluded:
# editing the glossary must not trigger a glossary review (a loop).
BASENAME="${FILE##*/}"
case "$BASENAME" in
  CONTEXT.md) exit 0 ;;
  CLAUDE.md|AGENTS.md) : ;;
  *.yaml|*.yml)
    case "$FILE" in */agents/*) : ;; *) exit 0 ;; esac
    ;;
  *) exit 0 ;;
esac

MARK="${TMPDIR:-/tmp}/domain-modeling-instredit.${SID}.fired"
[ -e "$MARK" ] && exit 0
[ -e "${TMPDIR:-/tmp}/grill-with-docs.${SID}.fired" ] && exit 0

[ -f "$INJECT_FILE" ] || exit 0
touch "$MARK" 2>/dev/null
jq -n --rawfile ctx "$INJECT_FILE" \
  '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
exit 0
