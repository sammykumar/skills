#!/usr/bin/env bash
# Configure the closest approximation of the vendored status line for Codex CLI.
#
# Codex cannot run a command for its status line. `tui.status_line` takes only a
# fixed enum of built-in items, so this picks the ones that line up with the
# sections the real renderer draws, in the same left-to-right order. It is an
# approximation by necessity, not a port. Safe to re-run.
set -euo pipefail

CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
CONFIG="$CODEX_DIR/config.toml"

mkdir -p "$CODEX_DIR"
[ -f "$CONFIG" ] || touch "$CONFIG"
cp "$CONFIG" "$CONFIG.bak-statusline-$(date +%Y%m%d-%H%M%S)"

python3 - "$CONFIG" <<'PY'
import re, sys

# Item names are the kebab-case serde values Codex accepts, ordered to mirror the
# renderer's layout: where you are, then what is running, then what it has cost.
ITEMS = [
    'project-name',           # path section
    'git-branch',             # branch section
    'branch-changes',         # the +/- counts
    'model-with-reasoning',   # model name and effort, which the renderer pairs
    'run-state',              # closest thing to the working/idle indicator
    'used-tokens',            # token total
    'context-used',           # context percentage
    'five-hour-limit',        # rate limit windows, which Codex reports and Copilot does not
    'weekly-limit',
]

path = sys.argv[1]
with open(path) as handle:
    text = handle.read()

block = (
    '[tui]\n'
    'status_line = [\n'
    + ''.join(f'    "{item}",\n' for item in ITEMS)
    + ']\n'
    'status_line_use_colors = true\n'
)

# A [tui] table may already exist with unrelated keys in it, so replace only the
# two keys this script owns and leave the rest of the table alone.
match = re.search(r'^\[tui\]\s*$', text, flags=re.MULTILINE)
if match:
    start = match.end()
    nxt = re.search(r'^\[', text[start:], flags=re.MULTILINE)
    end = start + (nxt.start() if nxt else len(text[start:]))
    body = text[start:end]
    body = re.sub(r'^\s*status_line\s*=\s*\[[^\]]*\]\s*$', '', body, flags=re.MULTILINE)
    body = re.sub(r'^\s*status_line_use_colors\s*=.*$', '', body, flags=re.MULTILINE)
    added = (
        '\nstatus_line = [\n'
        + ''.join(f'    "{item}",\n' for item in ITEMS)
        + ']\nstatus_line_use_colors = true\n'
    )
    text = text[:start] + added + body.lstrip('\n') + text[end:]
else:
    if text and not text.endswith('\n'):
        text += '\n'
    text += '\n' + block

with open(path, 'w') as handle:
    handle.write(text)
PY

echo "configured tui.status_line in $CONFIG"
echo
echo "Codex renders these from its own built-ins; it cannot run the real renderer."
echo "Adjust the selection any time with /statusline inside Codex."
