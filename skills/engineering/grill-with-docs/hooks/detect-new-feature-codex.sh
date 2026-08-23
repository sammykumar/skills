#!/usr/bin/env bash
# UserPromptSubmit hook (Codex CLI): Codex-side mirror of detect-new-feature.sh.
# Same keyword gate, same session fire-once, same injected context; the only
# difference is the confirm backend uses `codex exec` instead of `claude -p`.
#
# Set GRILL_CODEX_MODEL to a cheap model your Codex account can run; if unset,
# the confirm uses your configured default Codex model.
# Never names the user-invoked wrapper skill. Never exits non-zero on a no-op path.
# See README.md in this folder.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECT_FILE="$HOOK_DIR/injected-context.md"

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // empty')"
SID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
[ -n "$PROMPT" ] || exit 0
SID="${SID:-$PPID}"

MARK="${TMPDIR:-/tmp}/grill-with-docs.${SID}.fired"
[ -e "$MARK" ] && exit 0

GATE='(new feature|add(ing)? (a|an|support|the ability)|build(ing)? (a|an|out|the|me)|implement(ing)?|design(ing)? (a|an|the|for|our)|create (a|an|the|new)|introduc(e|ing) (a|an)|architect|how (should|do|would|can) (we|i) (build|design|structure|architect|approach|implement)|spec(ing| out| for)|greenfield|from scratch)'
printf '%s' "$PROMPT" | grep -iqE "$GATE" || exit 0

command -v codex >/dev/null 2>&1 || exit 0
CQ="You are a strict classifier for a coding agent. Decide whether the message below is proposing to BUILD A NEW FEATURE or make a non-trivial design or architecture decision that deserves an upfront design interview. Answer NO for bug fixes, debugging, questions, refactors, small edits, doc or config tweaks, or anything routine. Reply with exactly one word: YES or NO.

User message:
<<<
$PROMPT
>>>"

MODEL_ARGS=()
[ -n "${GRILL_CODEX_MODEL:-}" ] && MODEL_ARGS=(-m "$GRILL_CODEX_MODEL")
OUT="$(mktemp)"
printf '%s' "$CQ" | codex exec --skip-git-repo-check --ephemeral --ignore-rules \
  "${MODEL_ARGS[@]}" -o "$OUT" - >/dev/null 2>&1
RESP="$(tr '[:lower:]' '[:upper:]' < "$OUT" 2>/dev/null)"
rm -f "$OUT"
printf '%s' "$RESP" | grep -qE '\bYES\b' || exit 0
printf '%s' "$RESP" | grep -qE '\bNO\b' && exit 0

touch "$MARK" 2>/dev/null
[ -f "$INJECT_FILE" ] || exit 0
jq -n --rawfile ctx "$INJECT_FILE" \
  '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$ctx}}'
exit 0
