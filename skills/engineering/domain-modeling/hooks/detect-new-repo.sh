#!/usr/bin/env bash
# SessionStart hook (Claude Code and Codex): on a brand-new repo (no CONTEXT.md
# and fewer than 10 commits) nudge the model to start a domain glossary by
# invoking the `domain-modeling` skill. Standalone: no grilling.
#
# SessionStart additionalContext injection is verified on both harnesses, so a
# single shared script serves both. Fires on a fresh session only (not resume or
# post-compact), once per session, and stands down if the grill-with-docs hook
# already fired this session. Never names that wrapper. See README.md.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECT_FILE="$HOOK_DIR/new-repo-context.md"

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
SID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
SRC="$(printf '%s' "$INPUT" | jq -r '.source // empty')"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
SID="${SID:-$PPID}"
CWD="${CWD:-$PWD}"

# Fire on a genuinely fresh session only.
case "$SRC" in resume|compact) exit 0 ;; esac

# Fire once per session for this trigger type.
MARK="${TMPDIR:-/tmp}/domain-modeling-newrepo.${SID}.fired"
[ -e "$MARK" ] && exit 0

# Stand down if the design-interview hook already fired this session; it already
# puts domain-modeling in play.
[ -e "${TMPDIR:-/tmp}/grill-with-docs.${SID}.fired" ] && exit 0

# Must be inside a git work tree.
git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)"
[ -n "$ROOT" ] || exit 0

# Already has a domain model => nothing to bootstrap.
[ -e "$ROOT/CONTEXT.md" ] && exit 0
[ -e "$ROOT/CONTEXT-MAP.md" ] && exit 0

# Young repo only: fewer than 10 commits (no commits counts as young).
COUNT="$(git -C "$ROOT" rev-list --count HEAD 2>/dev/null)"
[ -n "$COUNT" ] || COUNT=0
[ "$COUNT" -ge 10 ] && exit 0

# Fire.
[ -f "$INJECT_FILE" ] || exit 0
touch "$MARK" 2>/dev/null
jq -n --rawfile ctx "$INJECT_FILE" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
exit 0
