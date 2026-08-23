#!/usr/bin/env bash
set -euo pipefail

# Cuts a repo's /ship command from the canonical template
# (.agents/ship-template.md) into <target-repo>/.claude/commands/ship.md.
#
# Usage:
#   scripts/scaffold-ship.sh /path/to/target-repo [default-branch]
#
# Strips the template's authoring header, substitutes {{DEFAULT_BRANCH}} (the
# arg, or the target repo's origin HEAD, or `main`), and leaves the GATES and
# DEPLOY `REPO:` zones as TODOs. After running, edit the target's ship.md to
# fill those zones with that repo's real gates and deploy story.
#
# Refuses to clobber an existing ship.md unless FORCE=1.

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$REPO/.agents/ship-template.md"
MARKER="=== SHIP COMMAND BODY BELOW ==="

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/scaffold-ship.sh /path/to/target-repo [default-branch]" >&2
  exit 2
fi

TARGET="$1"
BRANCH="${2:-}"

if [ ! -f "$TEMPLATE" ]; then
  echo "error: template not found at $TEMPLATE" >&2
  exit 1
fi

if [ ! -d "$TARGET/.git" ]; then
  echo "error: $TARGET is not a git repo (no .git dir)." >&2
  exit 1
fi

# Resolve the default branch: explicit arg wins, else the target's origin HEAD,
# else main.
if [ -z "$BRANCH" ]; then
  BRANCH="$(git -C "$TARGET" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')" || true
  BRANCH="${BRANCH:-main}"
fi

DEST_DIR="$TARGET/.claude/commands"
DEST="$DEST_DIR/ship.md"

if [ -e "$DEST" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "error: $DEST already exists. Re-run with FORCE=1 to overwrite." >&2
  exit 1
fi

mkdir -p "$DEST_DIR"

# Everything after the marker line is the command body; substitute the branch token.
sed -n "/^${MARKER}\$/,\$p" "$TEMPLATE" \
  | sed "1d; s/{{DEFAULT_BRANCH}}/${BRANCH}/g" \
  > "$DEST"

echo "wrote $DEST (default branch: $BRANCH)"
echo "next: fill the GATES and DEPLOY zones and the commit-message convention in that file."
