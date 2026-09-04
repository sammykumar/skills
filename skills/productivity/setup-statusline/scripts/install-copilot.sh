#!/usr/bin/env bash
# Install the vendored status line for GitHub Copilot CLI.
#
# Copilot uses the same contract as Claude Code (JSON on the command's stdin,
# ANSI on its stdout) with a different payload shape, so this points Copilot at
# the adapter, which translates and then calls the same renderer. Safe to re-run.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COPILOT_DIR="${COPILOT_HOME:-$HOME/.copilot}"
SETTINGS="$COPILOT_DIR/settings.json"
ADAPTER="$SKILL_DIR/scripts/copilot-statusline.py"

command -v python3 >/dev/null || { echo "error: python3 not found; the status line renderer needs it" >&2; exit 1; }
[ -d "$COPILOT_DIR" ] || { echo "error: $COPILOT_DIR not found; run copilot once first" >&2; exit 1; }

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-statusline-$(date +%Y%m%d-%H%M%S)"
else
  echo '{}' > "$SETTINGS"
fi

# `footer.showCustom` gates the custom line and defaults to on, so it only needs
# writing when a previous run or the /statusline picker turned it off.
STATUSLINE_CMD="python3 $ADAPTER" python3 - "$SETTINGS" <<'PY'
import json, os, sys

path = sys.argv[1]
with open(path) as handle:
    settings = json.load(handle)

settings['statusLine'] = {'type': 'command', 'command': os.environ['STATUSLINE_CMD']}
footer = settings.setdefault('footer', {})
footer['showCustom'] = True

with open(path, 'w') as handle:
    json.dump(settings, handle, indent=2)
    handle.write('\n')
PY

echo "configured statusLine in $SETTINGS"
echo
echo "Start a new copilot session to see it. Glyphs need a Nerd Font."
