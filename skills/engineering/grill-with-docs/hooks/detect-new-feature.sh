#!/usr/bin/env bash
# UserPromptSubmit hook (Claude Code): auto-start the design interview when a
# prompt is a clear new-feature / design ask. Keyword gate first, then a fast
# Haiku confirm; on a confirmed hit it injects context that tells the model to
# invoke the `grilling` + `domain-modeling` skills and record the design.
#
# Never names the user-invoked wrapper skill (naming it would make the model try
# to invoke a disable-model-invocation skill, which Claude Code blocks).
# Never exits non-zero on a no-op path: exit code 2 would BLOCK the user's prompt.
# See README.md in this folder.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECT_FILE="$HOOK_DIR/injected-context.md"

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // empty')"
SID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
[ -n "$PROMPT" ] || exit 0
SID="${SID:-$PPID}"

# Fire once per session.
MARK="${TMPDIR:-/tmp}/grill-with-docs.${SID}.fired"
[ -e "$MARK" ] && exit 0

# Keyword gate: clear feature / design language only. The confirm step below
# does the real disambiguation, so this errs toward catching candidates.
GATE='(new feature|add(ing)? (a|an|support|the ability)|build(ing)? (a|an|out|the|me)|implement(ing)?|design(ing)? (a|an|the|for|our)|create (a|an|the|new)|introduc(e|ing) (a|an)|architect|how (should|do|would|can) (we|i) (build|design|structure|architect|approach|implement)|spec(ing| out| for)|greenfield|from scratch)'
printf '%s' "$PROMPT" | grep -iqE "$GATE" || exit 0

# Confirm with a fast model. Missing CLI => do not fire (conservative).
command -v claude >/dev/null 2>&1 || exit 0
CQ="You are a strict classifier for a coding agent. Decide whether the message below is proposing to BUILD A NEW FEATURE or make a non-trivial design or architecture decision that deserves an upfront design interview. Answer NO for bug fixes, debugging, questions, refactors, small edits, doc or config tweaks, or anything routine. Reply with exactly one word: YES or NO.

User message:
<<<
$PROMPT
>>>"
RESP="$(printf '%s' "$CQ" | claude -p --model haiku 2>/dev/null | tr '[:lower:]' '[:upper:]')"
printf '%s' "$RESP" | grep -qE '\bYES\b' || exit 0
printf '%s' "$RESP" | grep -qE '\bNO\b' && exit 0

# Fire: mark the session and inject the workflow instructions.
touch "$MARK" 2>/dev/null
[ -f "$INJECT_FILE" ] || exit 0
jq -n --rawfile ctx "$INJECT_FILE" \
  '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$ctx}}'
exit 0
