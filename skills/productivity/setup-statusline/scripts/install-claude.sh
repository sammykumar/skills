#!/usr/bin/env bash
# Install the vendored status line for Claude Code.
#
# Symlinks the renderer into the Claude config dir and points settings.json at
# it. Symlinks rather than copies so editing the skill updates the live status
# line with no reinstall. Safe to re-run.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_DIR/settings.json"

command -v python3 >/dev/null || { echo "error: python3 not found; the status line renderer needs it" >&2; exit 1; }

mkdir -p "$CLAUDE_DIR/statusline"

# -n matters: without it, ln follows an existing symlink-to-directory and nests
# the new link inside the old target instead of replacing it.
ln -sfn "$SKILL_DIR/vendor/statusline_command.py" "$CLAUDE_DIR/statusline_command.py"
ln -sfn "$SKILL_DIR/vendor/statusline/themes.py"  "$CLAUDE_DIR/statusline/themes.py"
echo "linked renderer -> $CLAUDE_DIR/statusline_command.py"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-statusline-$(date +%Y%m%d-%H%M%S)"
else
  echo '{}' > "$SETTINGS"
fi

# Rewrite settings.json in python rather than with a text substitution, so an
# existing statusLine block is replaced and every other key is preserved.
STATUSLINE_CMD="python3 $CLAUDE_DIR/statusline_command.py" python3 - "$SETTINGS" <<'PY'
import json, os, sys

path = sys.argv[1]
with open(path) as handle:
    settings = json.load(handle)

settings['statusLine'] = {'type': 'command', 'command': os.environ['STATUSLINE_CMD']}

with open(path, 'w') as handle:
    json.dump(settings, handle, indent=2)
    handle.write('\n')
PY

echo "configured statusLine in $SETTINGS"
echo
echo "Start a new Claude Code session to see it. Glyphs need a Nerd Font."
