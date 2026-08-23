#!/usr/bin/env bash
# PostToolUse hook (Claude Code): when an edit touches this repo's agent-instruction
# files (CLAUDE.md, AGENTS.md, agents/*.yaml) nudge the model to reconcile the
# domain glossary by invoking the `domain-modeling` skill. Standalone: no grilling.
#
# Claude Code does not honor additionalContext on PostToolUse, so the nudge is
# delivered as exit-2 stderr: the tool has already run, the edit stands, and the
# text is surfaced to the model. See
# ../../../../.agents/adr/0005-lifecycle-triggers-inject-standalone-domain-modeling.md
# Fires once per session for this trigger type, and stands down if the
# grill-with-docs hook already fired. Never names that wrapper. See README.md.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECT_FILE="$HOOK_DIR/instruction-edit-context.md"

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
SID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')"
FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
SID="${SID:-$PPID}"

case "$TOOL" in Edit|Write|MultiEdit) ;; *) exit 0 ;; esac
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
# Deliver to the model as stderr; exit 2 surfaces it (the edit already applied).
cat "$INJECT_FILE" >&2
exit 2
