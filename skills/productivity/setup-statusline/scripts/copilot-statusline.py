#!/usr/bin/env python3
"""Render the vendored status line from a GitHub Copilot CLI payload.

Copilot CLI and Claude Code use the same status line contract: the harness spawns
a command, writes a JSON session object to its stdin, and renders whatever the
command prints to stdout. Only the shape of that JSON differs, so this script is
a translation layer, not a second renderer. It maps the Copilot payload onto the
dict that the vendored `SessionInfo.from_dict` already understands, then calls
the vendored `render()`.

Field names below were read from the payload Copilot CLI 1.0.82 actually emits,
captured from a live session, rather than from documentation.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

# Copilot renders every model as "<id> <sep> <effort>", e.g. "gpt-5.6-sol - medium".
# Splitting it lets the effort land in the field the renderer styles separately,
# instead of riding along inside the model name.
_EFFORT_SEP = '·'


def _load_renderer():
    """Import the vendored renderer as a module.

    The renderer is a top-level script, not an installed package, and it locates
    its own `statusline/themes.py` relative to its real path. Resolving symlinks
    here is what lets the installer link this script into `~/.copilot` while the
    renderer stays in the skill.
    """
    # The renderer reads its own supporting state (enabled plugins, token-rate
    # logs, theme override) out of a config dir it resolves from CLAUDE_CONFIG_DIR
    # at import time. Left alone it points at ~/.claude, which would put Claude
    # Code's plugin list and token history into a Copilot status line. Pointing it
    # at the Copilot config dir keeps each harness reporting its own state.
    os.environ.setdefault('CLAUDE_CONFIG_DIR', os.environ.get('COPILOT_HOME') or str(Path.home() / '.copilot'))
    # Render the session id as plain text rather than linking it to the Claude
    # resume handler, which would copy a `claude --resume` command for a session
    # only `copilot --resume` can reopen.
    os.environ.setdefault('SK_STATUSLINE_RESUME_SCHEME', '')

    override = os.environ.get('SK_STATUSLINE_RENDERER')
    path = Path(override) if override else Path(__file__).resolve().parent.parent / 'vendor' / 'statusline_command.py'
    if not path.is_file():
        raise SystemExit(f'statusline renderer not found at {path}')
    spec = importlib.util.spec_from_file_location('sk_statusline_renderer', path)
    if spec is None or spec.loader is None:
        raise SystemExit(f'could not load statusline renderer from {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules['sk_statusline_renderer'] = module
    spec.loader.exec_module(module)
    return module


def _split_model(display_name: str, model_id: str) -> tuple[str, str]:
    """Return (name, effort) from Copilot's combined `model.display_name`."""
    raw = (display_name or model_id or '').strip()
    if _EFFORT_SEP in raw:
        name, _, effort = raw.partition(_EFFORT_SEP)
        return name.strip(), effort.strip()
    return raw, ''


def _project_dir(cwd: str) -> str:
    """Nearest ancestor holding a `.git`, else the cwd itself.

    Claude Code sends `workspace.project_dir`; Copilot sends only `current_dir`.
    The renderer uses project_dir to find a project-level settings file, so an
    approximation is better than an empty string.
    """
    if not cwd:
        return ''
    current = Path(cwd)
    for candidate in (current, *current.parents):
        if (candidate / '.git').exists():
            return str(candidate)
    return cwd


def to_claude_payload(copilot: dict) -> dict:
    """Map a Copilot CLI status line payload onto the Claude Code shape.

    Fields Copilot has no equivalent for are left absent rather than invented, so
    the sections that depend on them omit themselves:

    - `rate_limits`: Copilot reports no 5-hour or weekly usage window.
    - `cost.total_cost_usd`: Copilot bills in AI credits (`ai_used`), not dollars.
      Copying a credit count into a dollar field would render a wrong number in a
      currency-labelled slot, so it stays unset.
    - `output_style`, `pr`, `agent`, `fast_mode`: no Copilot counterpart.
    """
    cwd = copilot.get('cwd') or ''
    workspace = copilot.get('workspace') or {}
    model = copilot.get('model') or {}
    cost = copilot.get('cost') or {}
    context = copilot.get('context_window') or {}

    name, effort = _split_model(model.get('display_name') or '', model.get('id') or '')

    # Copilot reports both a cumulative `used_percentage` across the session and a
    # live `current_context_used_percentage` for what is in the window right now.
    # Claude Code's `used_percentage` means the live one, so prefer that.
    used_pct = context.get('current_context_used_percentage')
    if used_pct is None:
        used_pct = context.get('used_percentage') or 0

    # `displayed_context_limit` is the limit actually in force for the selected
    # model and tier; `context_window_size` is the raw maximum.
    limit = context.get('displayed_context_limit') or context.get('context_window_size') or 0

    current_usage = context.get('current_usage') or {
        'input_tokens': context.get('last_call_input_tokens') or 0,
        'output_tokens': context.get('last_call_output_tokens') or 0,
        'cache_creation_input_tokens': context.get('total_cache_write_tokens') or 0,
        'cache_read_input_tokens': context.get('total_cache_read_tokens') or 0,
    }

    return {
        'session_id': copilot.get('session_id') or '',
        'session_name': copilot.get('session_name') or '',
        'transcript_path': copilot.get('transcript_path') or '',
        'cwd': cwd,
        'version': copilot.get('version') or '',
        'model': {'id': model.get('id') or '', 'display_name': name},
        'effort': {'level': effort},
        # The renderer only shows an effort level when thinking is on, and Copilot
        # states an effort for every model, so gate one on the other.
        'thinking': {'enabled': bool(effort)},
        'workspace': {
            'current_dir': workspace.get('current_dir') or cwd,
            'project_dir': _project_dir(cwd),
        },
        'cost': {
            'total_duration_ms': cost.get('total_duration_ms') or 0,
            'total_api_duration_ms': cost.get('total_api_duration_ms') or 0,
            'total_lines_added': cost.get('total_lines_added') or 0,
            'total_lines_removed': cost.get('total_lines_removed') or 0,
        },
        'context_window': {
            'total_input_tokens': context.get('total_input_tokens') or 0,
            'total_output_tokens': context.get('total_output_tokens') or 0,
            'context_window_size': limit,
            'current_usage': current_usage,
            'used_percentage': used_pct,
            'remaining_percentage': context.get('remaining_percentage'),
        },
        'exceeds_200k_tokens': bool(limit and limit > 200_000),
    }


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    theme_name = None
    args = sys.argv[1:]
    # `--map-only` prints the translated payload instead of rendering it, so the
    # mapping can be tested without depending on ANSI output staying byte-stable.
    map_only = False
    while args:
        arg = args.pop(0)
        if arg == '--theme' and args:
            theme_name = args.pop(0)
        elif arg.startswith('--theme='):
            theme_name = arg.split('=', 1)[1]
        elif arg == '--map-only':
            map_only = True

    copilot = json.loads(sys.stdin.read())
    payload = to_claude_payload(copilot)

    if map_only:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    renderer = _load_renderer()
    raw_width = renderer.terminal_width()
    if raw_width < renderer.MIN_WIDTH:
        return
    width = max(renderer.MIN_WIDTH, min(renderer.MAX_WIDTH, raw_width - 6))
    sys.stdout.write(renderer.render(payload, width, theme=renderer.resolve_theme(theme_name)))


if __name__ == '__main__':
    main()
