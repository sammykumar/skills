#!/usr/bin/env python3
'Claude Code statusLine command (Python port).'

from __future__ import annotations
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import NamedTuple


# Load the themes module via importlib because this script runs as a top-level
# file (not inside a package). The same shim is used by test/conftest.py.
_THEMES_PATH = Path(__file__).resolve().parent / 'statusline' / 'themes.py'
_themes_spec = importlib.util.spec_from_file_location('statusline_themes', _THEMES_PATH)
assert _themes_spec is not None and _themes_spec.loader is not None
themes = importlib.util.module_from_spec(_themes_spec)
sys.modules['statusline_themes'] = themes
_themes_spec.loader.exec_module(themes)
Theme        = themes.Theme
ModelColors  = themes.ModelColors
THEMES       = themes.THEMES
CLAUDE_DARK  = themes.CLAUDE_DARK


class BarChars:
    FILLED = '█'
    HEAVY  = '▆'
    MID    = ''
    EMPTY  = '░'


HOME       = Path(os.path.expanduser('~'))
CLAUDE_DIR = Path(os.environ.get('CLAUDE_CONFIG_DIR', str(HOME / '.claude')))
MIN_WIDTH    = 40
MAX_WIDTH    = 300
NARROW_WIDTH = 55
MEDIUM_WIDTH = 80
SOFT_LIMIT = 150_000
# Matches SGR (CSI m) sequences and OSC-8 hyperlinks (\x1b]8;;URL ST … \x1b]8;; ST,
# where ST is either BEL \x07 or ESC backslash \x1b\). Both forms must be
# stripped from width calculations.
OSC8_PREFIX = '\x1b]8;;'

# The border shows a trimmed session id — `claude -r <8 chars>` already filters
# the resume picker to one session — and links the full id to a URL-scheme
# handler that copies `claude --resume <uuid>` to the clipboard on click.
SESSION_ID_LEN = 8
# Overridable so a non-Claude harness can point the link at its own resume
# handler, or set it empty to render the session id as plain text. A Copilot
# session id resumes with `copilot --resume=<id>`, so linking it to the Claude
# handler would put the wrong command on the clipboard.
RESUME_SCHEME  = os.environ.get('SK_STATUSLINE_RESUME_SCHEME', 'claude-resume://')
_ANSI_RE   = re.compile(r'\x1b\[[0-9;]*m|\x1b\]8;;[^\x07\x1b]*(?:\x07|\x1b\\)')


def terminal_width() -> int:
    # Only ask tmux when we are actually inside it. Run from a non-tmux terminal
    # while any tmux server happens to be alive, `display-message -p` still
    # succeeds — it silently falls back to that server's most recently active
    # pane — so an unrelated background session would dictate the width here and
    # collapse wide layouts to medium. $TMUX is set only inside a tmux client;
    # $TMUX_PANE pins the query to our own pane rather than the active one.
    if os.environ.get('TMUX'):
        cmd = ["tmux", "display-message", "-p"]
        pane = os.environ.get('TMUX_PANE')
        if pane:
            cmd += ["-t", pane]
        cmd.append("'#{pane_width}'")
        try:
            w = int(subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout.strip().replace("'", ""))
            if w > 0:
                return w
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    try:
        w = int((CLAUDE_DIR / 'terminal-width').read_text().strip())
        if w > 0:
            return w
    except (OSError, ValueError):
        pass
    try:
        cols = int(os.environ.get('COLUMNS', '0'))
        if cols > 0:
            return cols
    except ValueError:
        pass
    w = shutil.get_terminal_size(fallback=(0, 0)).columns
    if w > 0:
        return w
    for fd in (2, 1, 0):
        try:
            return os.get_terminal_size(fd).columns
        except OSError:
            pass
    try:
        tty_fd = os.open('/dev/tty', os.O_RDONLY)
        try:
            return os.get_terminal_size(tty_fd).columns
        finally:
            os.close(tty_fd)
    except OSError:
        pass
    return MAX_WIDTH

RESET  = '\033[0m'
BOLD   = '\033[1m'
ITALIC = '\033[3m'

CLR_GREY_DIM   = '\033[38;5;244m'
CLR_GREY_DARK  = '\033[38;5;238m'
CLR_BORDER_OFF = '\033[38;5;242m'
CLR_SKY_BLUE   = '\033[38;5;75m'
CLR_GREEN_OK   = '\033[38;5;114m'
CLR_GREEN_DIM  = '\033[38;5;77m'
CLR_GREEN_BRT  = '\033[38;5;46m'
CLR_PURPLE     = '\033[38;5;183m'
CLR_GOLD       = '\033[38;5;222m'
CLR_YELLOW     = '\033[38;5;226m'
CLR_YELLOW_BRT = '\033[38;5;11m'
CLR_CYAN       = '\033[38;5;116m'
CLR_CYAN_DIM   = '\033[38;5;244m'
CLR_CYAN_DAY   = '\033[38;5;109m'
CLR_CYAN_DAY_DIM = '\033[38;5;240m'
CLR_CYAN_ICON  = '\033[38;5;117m'
CLR_PINK       = '\033[38;5;210m'
CLR_PEACH      = '\033[38;5;216m'
CLR_WHITE_BRT  = '\033[38;5;15m'
CLR_WARN       = '\033[38;5;214m'
CLR_ALERT      = '\033[38;5;167m'

# Nerd Font Private Use Area glyphs. Encoded as escapes so Edit, diff, and
# chat round-trips never lose the bytes. Render only in a Nerd-Font-capable
# terminal.
ICON_COST     = '\uefc8'      # nf-md currency-usd  (cost row)
ICON_TOK_RATE = '\U000f18a7'  # nf-md gauge         (t/m rate label)
GLYPH_MODEL    = '\U000f08b9' # nf-md-monitor-dashboard
GLYPH_THINKING = '\U000f1a53' # nf-md-brain
GLYPH_FAST     = '\uef76'     # nf-cod-zap (shown when fast_mode is on)
GLYPH_FOLDER   = '\uef85'     # nf-custom folder    (path row)
GLYPH_WORKTREE = '\uf402'     # nf-oct-repo_forked  (path row, linked worktree)
GLYPH_BRANCH   = '\ue725'     # nf-dev-git_branch   (branch marker)
GLYPH_COMMIT   = '\uf417'     # nf-oct-git_commit   (branch marker, detached HEAD)
GLYPH_PR       = '\uf407'     # nf-oct-git_pull_request (open PR badge)
GLYPH_WARNING  = '\uf071'     # nf-fa-warning       (context in the alert zone)
GLYPH_SUBAGENT = '\uf135'     # nf-fa-tasks         (subagent list)
GLYPH_SUBAGENT_ROW = '\u25b6'  # \u25b6 U+25B6           (per-row Running Subagent marker)
GLYPH_TASKS    = '\U000f0755'  # nf-md format-list-checks (Task Row marker)
GLYPH_SKILLS  = ''      # nf-fa-magic wand    (skills label)
GLYPH_PLUGINS = '\uf1e6'      # nf-fa-plug          (plugins label)
GLYPH_HELPER   = '\uf4cd'     # nf-mdi-star_circle  (5h rate-limit helper)
GLYPH_WEEKLY   = '\uf073'     # nf-fa-calendar      (7-day rate-limit usage)
GLYPH_TRASH    = '\U000f0a7a' # nf-md-trash_can     (git deleted count)
GLYPH_RENAMED  = '\U000f1031' # nf-md-file_move     (git renamed count)
GLYPH_CONTINUATION = '└'    # U+2514 BOX DRAWINGS LIGHT UP AND RIGHT (└)
GLYPH_REPLYING     = '\U000f0189'  # nf-md-message  (replying state)
GLYPH_HOURGLASS    = '\uf253'  # nf-fa-hourglass_half (subagent context size)
GLYPH_SESSION_NAME = '\U000f04fc'  # nf-md-tag         (custom session name)
SESSION_NAME_GLYPH_FG = '\033[38;2;253;151;31m'  # Monokai orange (#FD971F) for session-name glyph
GLYPH_MONITOR      = ''      # nf-fa-eye         (Monitor tool invocation)

GLYPH_WORKING  = '\U000f0493'  # nf-md-cog   (working: gear)
GLYPH_IDLE     = '\U000f04b2'  # nf-md-sleep (idle: Zzz)

ACTIVITY_STATE_DIR = Path('/tmp/claude-statusline-sessions')

TOOL_ARG_KEY: dict[str, str] = {
    'Bash':        'command',
    'Read':        'file_path',
    'Edit':        'file_path',
    'Write':       'file_path',
    'NotebookEdit':'file_path',
    'Grep':        'pattern',
    'Glob':        'pattern',
    'Task':        'subagent_type',
}

# Dim factor for the in-flight (currently-open) sparkline bucket.
LIVE_DIM = 0.5

# Sparkline slope glyphs from U+1FB3C–U+1FB6B "Symbols for Legacy Computing".
# Used by GradientEngine.sparkline to draw sloped peaks: a "rise" char on the
# peak cell pairs with a "fall" char on the next cell to form a /\ shape.
SPARK_RISE_SMALL  = '\U0001fb48'  # 🭈 small rise (bot row, idx 1–3)
SPARK_FALL_SMALL  = '\U0001fb3d'  # 🬽 small fall (bot row, idx 1–3)
SPARK_RISE_MED    = '\U0001fb4a'  # 🭊 medium rise (bot row, idx 4–7)
SPARK_FALL_MED    = '\U0001fb3f'  # 🬿 medium fall (bot row, idx 4–7)
SPARK_RISE_TALL   = '\U0001fb45'  # 🭅 tall rise (bot row, idx 8+)
SPARK_FALL_TALL   = '\U0001fb50'  # 🭐 tall fall (bot row, idx 8+)
SPARK_RISE_TOP    = '\U0001fb4b'  # 🭋 top-row rise (idx 9+)
SPARK_FALL_TOP    = '\U0001fb40'  # 🭀 top-row fall (idx 9+)

def _is_wide(ch: str) -> bool:
    cp = ord(ch)
    # Supplemental Arrows-C (U+1F800-U+1F8FF) are EAW=N despite being in the
    # emoji range — exclude them so arrow icons like 🡅/🡇 count as 1 col.
    if 0x1F800 <= cp <= 0x1F8FF:
        return False
    return 0x1F300 <= cp <= 0x1FAFF


def _visible_width(s: str) -> int:
    plain = _ANSI_RE.sub('', s)
    return sum(2 if _is_wide(ch) else 1 for ch in plain)


def _truncate_visible(text: str, max_w: int) -> str:
    """Trim to `max_w` visible columns, keeping escapes intact.

    Styled text can't be sliced by character: cutting inside a CSI sequence
    prints its tail as literal text, and cutting inside an OSC-8 hyperlink
    leaves the link open so every later cell on the row inherits it.
    """
    if max_w <= 0:
        return ''
    if _visible_width(text) <= max_w:
        return text

    out: list[str] = []
    seen = 0
    link_open = False
    i = 0
    while i < len(text):
        m = _ANSI_RE.match(text, i)
        if m:
            esc = m.group()
            if esc.startswith(OSC8_PREFIX):
                # `\x1b]8;;<url><terminator>` opens a link; an empty url closes it.
                link_open = bool(esc[len(OSC8_PREFIX):].rstrip('\x07\x1b\\'))
            out.append(esc)
            i = m.end()
            continue
        if seen >= max_w - 1:
            break
        out.append(text[i])
        seen += _visible_width(text[i])
        i += 1
    out.append('…')
    if link_open:
        out.append(f'{OSC8_PREFIX}\x1b\\')
    out.append(RESET)
    return ''.join(out)


def abbreviate_ancestors(short_pwd: str, keep_tail: int) -> str:
    """Shorten every segment above the repo to its initial: `~/D/S/p/perch.martech`.

    `keep_tail` is how many trailing segments belong to the repo (its own
    directory plus anything below it) — those are never touched, because they
    are the part that says which checkout you are in.
    """
    parts = short_pwd.split('/')
    keep  = max(1, keep_tail)
    if len(parts) <= keep:
        return short_pwd
    head, tail = parts[:-keep], parts[-keep:]
    short_head = [
        seg if seg in ('~', '') else (seg[:2] if seg.startswith('.') else seg[:1])
        for seg in head
    ]
    return '/'.join(short_head + tail)


def _middle_ellipsis(text: str, max_w: int) -> str:
    if max_w <= 1:
        return '…'
    if _visible_width(text) <= max_w:
        return text
    left_vis  = (max_w - 1) // 2
    right_vis = max_w - 1 - left_vis

    # Tokenise into (is_escape, string) pairs to preserve ANSI across the cut.
    tokens: list[tuple[bool, str]] = []
    i = 0
    while i < len(text):
        m = _ANSI_RE.match(text, i)
        if m:
            tokens.append((True, m.group()))
            i = m.end()
        else:
            tokens.append((False, text[i]))
            i += 1

    def _take(toks: list[tuple[bool, str]], n: int) -> list[str]:
        out: list[str] = []
        seen = 0
        for is_esc, tok in toks:
            if is_esc:
                out.append(tok)
            elif seen < n:
                out.append(tok)
                seen += 1
            else:
                break
        return out

    prefix = _take(tokens, left_vis)
    suffix = _take(list(reversed(tokens)), right_vis)
    suffix.reverse()

    result = ''.join(prefix) + '…' + ''.join(suffix)
    if _visible_width(result) <= max_w:
        return result
    # Trim one visible char from prefix to fix wide-char overshoot.
    for j in range(len(prefix) - 1, -1, -1):
        if not _ANSI_RE.fullmatch(prefix[j]):
            prefix.pop(j)
            break
    return ''.join(prefix) + '…' + ''.join(suffix)


class TokenAccounting:
    @staticmethod
    def rates_for(model_name: str) -> tuple[float, float]:
        m = model_name.lower()
        if 'opus' in m:
            return 15.00, 75.00
        if 'haiku' in m:
            return 0.80, 4.00
        return 3.00, 15.00

    @staticmethod
    def session_cost(model: Model, usage: TranscriptUsage) -> float:
        rate_in, rate_out = TokenAccounting.rates_for(
            model.display_name or model.id
        )
        cost = (
            usage.input_tokens * rate_in
            + usage.cache_creation_input_tokens * rate_in * 1.25
            + usage.cache_read_input_tokens * rate_in * 0.1
            + usage.output_tokens * rate_out
        )
        return cost / 1_000_000

    @staticmethod
    def day_cost(model: Model, token_log: TokenLog) -> float:
        rate_in, rate_out = TokenAccounting.rates_for(
            model.display_name or model.id
        )
        cost = (
            token_log.day_in * rate_in
            + token_log.day_cache_read * rate_in * 0.1
            + token_log.day_out * rate_out
        )
        return cost / 1_000_000


class Model(NamedTuple):
    id: str = ''
    display_name: str = ''

    @classmethod
    def from_dict(cls, d) -> Model:
        if isinstance(d, str):
            return cls(id=d, display_name='')
        return cls(id=d.get('id', ''), display_name=d.get('display_name', ''))

    @property
    def cost_rates(self) -> tuple[float, float]:
        return TokenAccounting.rates_for(self.display_name or self.id)


class OutputStyle(NamedTuple):
    name: str = 'default'

    @classmethod
    def from_dict(cls, d: dict) -> OutputStyle:
        return cls(name=d.get('name', 'default'))


class Effort(NamedTuple):
    level: str = ''

    @classmethod
    def from_dict(cls, d: dict) -> Effort:
        return cls(level=d.get('level', ''))


class Thinking(NamedTuple):
    enabled: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> Thinking:
        return cls(enabled=bool(d.get('enabled', False)))


class CurrentUsage(NamedTuple):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> CurrentUsage:
        return cls(
            input_tokens                = d.get('input_tokens', 0),
            output_tokens               = d.get('output_tokens', 0),
            cache_creation_input_tokens = d.get('cache_creation_input_tokens', 0),
            cache_read_input_tokens     = d.get('cache_read_input_tokens', 0),
        )


class RateBucket(NamedTuple):
    used_percentage: float = 0.0
    resets_at: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> RateBucket:
        return cls(
            used_percentage = round(float(d.get('used_percentage', 0.0)), 2),
            resets_at       = d.get('resets_at', 0),
        )


@dataclass
class Repo:
    """`workspace.repo` — present inside a git repo with an `origin` remote."""
    host: str = ''
    owner: str = ''
    name: str = ''

    @classmethod
    def from_dict(cls, d: dict) -> Repo:
        return cls(
            host  = d.get('host', ''),
            owner = d.get('owner', ''),
            name  = d.get('name', ''),
        )

    @property
    def url(self) -> str:
        if not (self.host and self.owner and self.name):
            return ''
        return f'https://{self.host}/{self.owner}/{self.name}'


@dataclass
class Pr:
    """`pr` — present only while an open PR exists for the current branch."""
    number: int = 0
    url: str = ''
    review_state: str = ''  # may be absent independently of the rest

    @classmethod
    def from_dict(cls, d: dict) -> Pr:
        return cls(
            number       = int(d.get('number') or 0),
            url          = d.get('url', ''),
            review_state = d.get('review_state') or '',
        )


@dataclass
class Agent:
    """`agent` — present when running under `--agent` or agent settings."""
    name: str = ''

    @classmethod
    def from_dict(cls, d: dict) -> Agent:
        return cls(name=d.get('name', ''))


@dataclass
class Workspace:
    current_dir: str = ''
    project_dir: str = ''
    added_dirs: list = field(default_factory=list)
    git_worktree: str = ''  # linked-worktree name; absent outside a worktree
    repo: Repo = field(default_factory=Repo)

    @classmethod
    def from_dict(cls, d: dict) -> Workspace:
        return cls(
            current_dir  = d.get('current_dir', ''),
            project_dir  = d.get('project_dir', ''),
            added_dirs   = d.get('added_dirs') or [],
            # Present only when the cwd sits inside a linked worktree.
            git_worktree = d.get('git_worktree') or '',
            repo         = Repo.from_dict(d.get('repo') or {}),
        )

    @property
    def plugins(self) -> str:
        seen: dict[str, None] = {}
        candidates = [CLAUDE_DIR / 'settings.json']
        if self.project_dir:
            candidates.append(Path(self.project_dir) / '.claude' / 'settings.json')
        for sf in candidates:
            if not sf.is_file():
                continue
            try:
                data = json.loads(sf.read_text())
            except Exception:
                continue
            for key, val in (data.get('enabledPlugins') or {}).items():
                if val is True:
                    name = key.split('@', 1)[0]
                    if name not in seen:
                        seen[name] = None
        return ','.join(seen.keys())


@dataclass
class Cost:
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    total_api_duration_ms: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> Cost:
        return cls(
            total_cost_usd        = d.get('total_cost_usd', 0.0),
            total_duration_ms     = d.get('total_duration_ms', 0),
            total_api_duration_ms = d.get('total_api_duration_ms', 0),
            total_lines_added     = d.get('total_lines_added', 0),
            total_lines_removed   = d.get('total_lines_removed', 0),
        )


@dataclass
class ContextWindow:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    context_window_size: int = 0
    current_usage: CurrentUsage = field(default_factory=CurrentUsage)
    used_percentage: float | None = None
    remaining_percentage: float | None = None

    @classmethod
    def from_dict(cls, d: dict) -> ContextWindow:
        return cls(
            total_input_tokens   = d.get('total_input_tokens', 0),
            total_output_tokens  = d.get('total_output_tokens', 0),
            context_window_size  = d.get('context_window_size', 0),
            current_usage        = CurrentUsage.from_dict(d.get('current_usage') or {}),
            used_percentage      = d.get('used_percentage'),
            remaining_percentage = d.get('remaining_percentage'),
        )


@dataclass
class RateLimits:
    five_hour: RateBucket = field(default_factory=RateBucket)
    seven_day: RateBucket = field(default_factory=RateBucket)

    @classmethod
    def from_dict(cls, d: dict) -> RateLimits:
        return cls(
            five_hour = RateBucket.from_dict(d.get('five_hour')  or {}),
            seven_day = RateBucket.from_dict(d.get('seven_day') or {}),
        )


@dataclass
class SessionInfo:
    session_id: str = ''
    session_name: str = ''
    transcript_path: str = ''
    cwd: str = ''
    model: Model = field(default_factory=Model)
    workspace: Workspace = field(default_factory=Workspace)
    version: str = ''
    output_style: OutputStyle = field(default_factory=OutputStyle)
    cost: Cost = field(default_factory=Cost)
    context_window: ContextWindow = field(default_factory=ContextWindow)
    exceeds_200k_tokens: bool = False
    effort: Effort = field(default_factory=Effort)
    thinking: Thinking = field(default_factory=Thinking)
    fast_mode: bool = False
    rate_limits: RateLimits = field(default_factory=RateLimits)
    pr: Pr = field(default_factory=Pr)
    agent: Agent = field(default_factory=Agent)

    @classmethod
    def from_dict(cls, d: dict) -> SessionInfo:
        return cls(
            session_id          = d.get('session_id', ''),
            # Set by --name / /rename, or once an AI title exists.
            session_name        = d.get('session_name') or '',
            transcript_path     = d.get('transcript_path', ''),
            cwd                 = d.get('cwd', ''),
            model               = Model.from_dict(d.get('model') or {}),
            workspace           = Workspace.from_dict(d.get('workspace') or {}),
            version             = d.get('version', ''),
            output_style        = OutputStyle.from_dict(d.get('output_style') or {}),
            cost                = Cost.from_dict(d.get('cost') or {}),
            context_window      = ContextWindow.from_dict(d.get('context_window') or {}),
            exceeds_200k_tokens = d.get('exceeds_200k_tokens', False),
            effort              = Effort.from_dict(d.get('effort') or {}),
            thinking            = Thinking.from_dict(d.get('thinking') or {}),
            fast_mode           = bool(d.get('fast_mode', False)),
            rate_limits         = RateLimits.from_dict(d.get('rate_limits') or {}),
            pr                  = Pr.from_dict(d.get('pr') or {}),
            agent               = Agent.from_dict(d.get('agent') or {}),
        )

    @property
    def short_pwd(self) -> str:
        home = str(HOME)
        p = self.cwd
        if p.startswith(home):
            p = '~' + p[len(home):]
        return p

    @property
    def model_name(self) -> str:
        name = self.model.display_name or self.model.id or 'unknown'
        return name.replace('(1M context)', '1M').replace('  ', ' ').strip()

    @property
    def model_thinking(self) -> str:
        if self.thinking.enabled and self.effort.level:
            return f'{self.effort.level}/fast' if self.fast_mode else self.effort.level
        if self.fast_mode:
            return 'fast'
        return ''

    @property
    def plugin_names(self) -> str:
        return self.workspace.plugins


def fmt_duration_ms(total_duration_ms: int) -> str:
    """Session wall-clock from `cost.total_duration_ms`, as `2h5m` / `45m`. '' when unset."""
    if not total_duration_ms:
        return ''
    total_m = int(total_duration_ms) // 60_000
    h, m    = divmod(total_m, 60)
    return f'{h}h{m}m' if h else f'{m}m'


def compute_session_cost(model: Model, usage: TranscriptUsage) -> float:
    return TokenAccounting.session_cost(model, usage)


def compute_day_cost(model: Model, token_log: TokenLog) -> float:
    return TokenAccounting.day_cost(model, token_log)


@dataclass
class TokenLog:
    day_in: int = 0
    day_cache_read: int = 0
    day_out: int = 0

    @classmethod
    def update(cls, session_id: str, today: str, total_in: int, cache_read: int, total_out: int) -> TokenLog:
        log = CLAUDE_DIR / 'statusline-tokens.log'
        lines = []
        if log.exists():
            for ln in log.read_text().splitlines():
                parts = ln.split()
                if len(parts) >= 2 and parts[1] == session_id:
                    continue
                lines.append(ln)
        if session_id and (total_in > 0 or cache_read > 0 or total_out > 0):
            lines.append(f'{today} {session_id} {total_in} {cache_read} {total_out}')
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text('\n'.join(lines) + '\n')
        day_in = day_cache_read = day_out = 0
        for ln in lines:
            parts = ln.split()
            if len(parts) < 4 or parts[0] != today:
                continue
            try:
                if len(parts) == 6:
                    day_in += int(parts[2])
                    day_out += int(parts[3])
                elif len(parts) >= 5:
                    day_in += int(parts[2])
                    day_cache_read += int(parts[3])
                    day_out += int(parts[4])
                else:
                    day_in += int(parts[2])
                    day_out += int(parts[3])
            except ValueError:
                pass
        return cls(day_in=day_in, day_cache_read=day_cache_read, day_out=day_out)



class TokenRate:
    WINDOW = float(os.environ.get('STATUSLINE_TOKEN_WINDOW', '60'))
    KEEP = 300.0

    @classmethod
    def update(cls, session_id: str, total_in: int, total_out: int) -> int:
        if not session_id:
            return 0
        log = CLAUDE_DIR / 'statusline-token-rate.log'
        now = time.time()
        rows: list[tuple[float, str, int, int]] = []
        if log.exists():
            for ln in log.read_text().splitlines():
                parts = ln.split()
                if len(parts) < 4:
                    continue
                try:
                    ts = float(parts[0])
                    ti = int(parts[2])
                    to = int(parts[3])
                except ValueError:
                    continue
                if now - ts > cls.KEEP:
                    continue
                rows.append((ts, parts[1], ti, to))
        rows.append((now, session_id, total_in, total_out))
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text('\n'.join(f'{ts:.3f} {sid} {ti} {to}' for ts, sid, ti, to in rows) + '\n')
        except OSError:
            pass
        samples = [(ts, ti, to) for ts, sid, ti, to in rows if sid == session_id and now - ts <= cls.WINDOW]
        if len(samples) < 2:
            return 0
        samples.sort()
        _, ti0, to0 = samples[0]
        _, ti1, to1 = samples[-1]
        return max(0, (ti1 + to1) - (ti0 + to0))

    @classmethod
    def history(cls, session_id: str, n_buckets: int, window: float) -> list[int]:
        if n_buckets <= 0 or not session_id:
            return []
        log = CLAUDE_DIR / 'statusline-token-rate.log'
        now = time.time()
        samples: list[tuple[float, int, int]] = []
        if log.exists():
            for ln in log.read_text().splitlines():
                parts = ln.split()
                if len(parts) < 4:
                    continue
                try:
                    ts = float(parts[0])
                    sid = parts[1]
                    ti = int(parts[2])
                    to = int(parts[3])
                except ValueError:
                    continue
                if sid == session_id and now - ts <= window + window / n_buckets:
                    samples.append((ts, ti, to))
        if len(samples) < 2:
            return [0] * n_buckets
        samples.sort()
        bucket_size = window / n_buckets
        last_bucket  = int(now // bucket_size)
        first_bucket = last_bucket - n_buckets + 1
        buckets = [0] * n_buckets
        for i in range(len(samples) - 1):
            ts0, ti0, to0 = samples[i]
            ts1, ti1, to1 = samples[i + 1]
            delta = max(0, (ti1 + to1) - (ti0 + to0))
            if delta == 0:
                continue
            midpoint = (ts0 + ts1) / 2
            abs_bucket = int(midpoint // bucket_size)
            if first_bucket <= abs_bucket <= last_bucket:
                buckets[abs_bucket - first_bucket] += delta
        return buckets

    @classmethod
    def recently_active(cls, session_id: str, window: float = 10.0) -> tuple[bool, bool]:
        """Return (in_active, out_active) — True if that count grew in the last `window` seconds."""
        if not session_id:
            return False, False
        log = CLAUDE_DIR / 'statusline-token-rate.log'
        if not log.exists():
            return False, False
        now = time.time()
        samples: list[tuple[float, int, int]] = []
        for ln in log.read_text().splitlines():
            parts = ln.split()
            if len(parts) < 4:
                continue
            try:
                ts, sid, ti, to = float(parts[0]), parts[1], int(parts[2]), int(parts[3])
            except ValueError:
                continue
            if sid == session_id and now - ts <= window:
                samples.append((ts, ti, to))
        if len(samples) < 2:
            return False, False
        samples.sort()
        ti0, to0 = samples[0][1], samples[0][2]
        ti1, to1 = samples[-1][1], samples[-1][2]
        return ti1 > ti0, to1 > to0


@dataclass
class ActivityState:
    is_working: bool = False

    @classmethod
    def from_session(cls, session_id: str) -> ActivityState:
        if not session_id:
            return cls()
        try:
            state = (ACTIVITY_STATE_DIR / f'{session_id}.state').read_text().strip()
        except OSError:
            return cls()
        return cls(is_working=(state == 'working'))


@dataclass
class Monitor:
    description: str
    started_at: float


@dataclass
class RunningMonitors:
    monitors: list[Monitor]

    @classmethod
    def from_session(cls, session_id: str) -> RunningMonitors:
        if not session_id:
            return cls(monitors=[])
        mdir = ACTIVITY_STATE_DIR / f'{session_id}.monitors'
        try:
            entries = sorted(mdir.iterdir(), key=lambda p: p.stat().st_mtime)
        except OSError:
            return cls(monitors=[])
        out: list[Monitor] = []
        for f in entries:
            try:
                raw = f.read_text()
            except OSError:
                continue
            ts_s, _, desc = raw.partition('\t')
            try:
                started_at = float(ts_s)
            except ValueError:
                continue
            out.append(Monitor(description=desc.strip(), started_at=started_at))
        return cls(monitors=out)


@dataclass
class SessionName:
    name: str = ''

    @classmethod
    def lookup(cls, session_id: str, transcript_path: str = '') -> SessionName:
        if not session_id:
            return cls()
        sessions_dir = CLAUDE_DIR / 'sessions'
        try:
            files = list(sessions_dir.glob('*.json'))
        except OSError:
            files = []
        for f in files:
            try:
                data = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if data.get('sessionId') == session_id:
                name = data.get('name') or ''
                if name:
                    return cls(name=str(name))
                break
        if transcript_path:
            p = Path(transcript_path)
            if p.is_file():
                title = ''
                try:
                    with p.open('r', errors='ignore') as fh:
                        for ln in fh:
                            if '"ai-title"' not in ln:
                                continue
                            try:
                                d = json.loads(ln)
                            except (ValueError, TypeError):
                                continue
                            if d.get('type') == 'ai-title':
                                t = d.get('aiTitle') or ''
                                if t:
                                    title = str(t)
                except OSError:
                    pass
                if title:
                    return cls(name=title)
        return cls()


def github_url_from_remote(remote_url: str) -> str:
    """Convert a git origin URL to its https://github.com/owner/repo form, or ''."""
    s = remote_url.strip()
    if s.startswith('git@github.com:'):
        path = s[len('git@github.com:'):]
    elif s.startswith('ssh://git@github.com/'):
        path = s[len('ssh://git@github.com/'):]
    elif s.startswith('https://github.com/'):
        path = s[len('https://github.com/'):]
    else:
        return ''
    return f'https://github.com/{path.removesuffix(".git")}'


def short_session_id(session_id: str) -> str:
    return session_id[:SESSION_ID_LEN]


def resume_url(session_id: str) -> str:
    if not (session_id and RESUME_SCHEME):
        return ''
    return f'{RESUME_SCHEME}{session_id}'


def osc8(url: str, text: str) -> str:
    """Wrap text in an OSC-8 hyperlink. Returns text unchanged if url is empty."""
    if not url:
        return text
    return f'{OSC8_PREFIX}{url}\x1b\\{text}{OSC8_PREFIX}\x1b\\'


@dataclass
class GitInfo:
    branch: str = ''
    commit: str = ''
    modified: int = 0
    untracked: int = 0
    deleted: int = 0
    renamed: int = 0
    remote_url: str = ''  # https://github.com/owner/repo form when origin is github
    is_worktree: bool = False
    repo_tail: int = 1  # trailing path segments owned by the repo

    @classmethod
    def from_cwd(cls, cwd: str, worktree_hint: str = '', remote_hint: str = '') -> GitInfo:
        repo, gitdir   = cls._find_repo(cwd)
        branch, commit = cls._read_head(gitdir)
        modified = untracked = deleted = renamed = 0
        remote_url = remote_hint
        if branch:
            modified, untracked, deleted, renamed = cls._dirty(repo)
            # `workspace.repo` already tells us the origin — only shell out when
            # the harness didn't supply it (no origin, or an older CC).
            remote_url = remote_hint or cls._remote_url(repo)
        # Claude Code passes `workspace.git_worktree` when the cwd is inside a
        # linked worktree; fall back to the layout on disk when it doesn't. A
        # linked worktree's admin dir is `<common>/worktrees/<name>`; a
        # submodule's is `<super>/modules/<name>`, which is not a worktree.
        is_worktree = bool(worktree_hint) or (bool(gitdir) and Path(gitdir).parent.name == 'worktrees')
        return cls(
            repo_tail   = cls._repo_tail(cwd, gitdir),
            branch      = branch,
            commit      = commit,
            modified    = modified,
            untracked   = untracked,
            deleted     = deleted,
            renamed     = renamed,
            remote_url  = remote_url,
            is_worktree = is_worktree,
        )

    @staticmethod
    def _remote_url(repo: str) -> str:
        if not repo:
            return ''
        try:
            r = subprocess.run(
                ['git', '-C', repo, 'remote', 'get-url', 'origin'],
                capture_output=True, text=True, timeout=2,
            )
        except Exception:
            return ''
        if r.returncode != 0:
            return ''
        return github_url_from_remote(r.stdout)

    @staticmethod
    def _find_repo(cwd: str) -> tuple[str, str]:
        curr = Path(cwd) if cwd else None
        while curr:
            dot_git = curr / '.git'
            if dot_git.is_file():
                # Linked worktree or submodule: `.git` is a file holding
                # `gitdir: <path to the real admin dir>`.
                try:
                    pointer = dot_git.read_text().strip()
                except OSError:
                    pointer = ''
                if pointer.startswith('gitdir:'):
                    target = Path(pointer.split(':', 1)[1].strip())
                    if not target.is_absolute():
                        target = (curr / target).resolve()
                    return str(curr), str(target)
            elif dot_git.exists():
                return str(curr), str(dot_git)
            if curr == curr.parent:
                break
            curr = curr.parent
        return '', ''

    @staticmethod
    def _repo_tail(cwd: str, gitdir: str) -> int:
        """Segments of `cwd` from the main repo's directory down, minimum 1.

        Measured from the *common* dir, so a worktree parked inside its own
        repo still counts the repo directory itself as part of the tail.
        """
        if not (cwd and gitdir):
            return 1
        try:
            main_root = GitInfo._common_dir(gitdir).parent.resolve()
            rel = Path(cwd).resolve().relative_to(main_root)
        except (ValueError, OSError):
            return 1
        return 1 + len(rel.parts)

    @staticmethod
    def _common_dir(gitdir: str) -> Path:
        """Shared ref store. A worktree admin dir points at it via `commondir`."""
        base = Path(gitdir)
        cd   = base / 'commondir'
        if not cd.is_file():
            return base
        try:
            target = Path(cd.read_text().strip())
        except OSError:
            return base
        return target if target.is_absolute() else (base / target).resolve()

    @staticmethod
    def _resolve_ref(common: Path, branch: str) -> str:
        """Tip commit for `branch`, loose ref first then packed-refs. '' when unknown."""
        loose = common / 'refs' / 'heads' / Path(branch)
        if loose.is_file():
            try:
                return loose.read_text().strip()[:9]
            except OSError:
                pass
        packed = common / 'packed-refs'
        if packed.is_file():
            want = f'refs/heads/{branch}'
            try:
                for line in packed.read_text().splitlines():
                    if not line or line[0] in '#^':
                        continue
                    sha, _, ref = line.partition(' ')
                    if ref.strip() == want:
                        return sha[:9]
            except OSError:
                pass
        return ''

    @staticmethod
    def _read_head(gitdir: str) -> tuple[str, str]:
        if not gitdir:
            return '', ''
        head_path = Path(gitdir) / 'HEAD'
        if not head_path.is_file():
            return '', ''
        try:
            head = head_path.read_text().strip()
        except OSError:
            return '', ''
        branch = ''
        if head.startswith('ref:'):
            ref = head.split(':', 1)[1].strip()
            # Keep the full name: `feature/pdds`, not `pdds` — the ref lookup
            # below needs it, and the truncated form is ambiguous anyway.
            branch = ref[len('refs/heads/'):] if ref.startswith('refs/heads/') else ref.rsplit('/', 1)[-1]
        elif head:
            branch = f'd:{head[:7]}'
        commit = ''
        if branch and not branch.startswith('d:'):
            commit = GitInfo._resolve_ref(GitInfo._common_dir(gitdir), branch)
        if not commit:
            orig = Path(gitdir) / 'ORIG_HEAD'
            if orig.is_file():
                try:
                    commit = orig.read_text().strip()[:9]
                except OSError:
                    pass
        return branch, commit

    @staticmethod
    def _dirty(repo: str) -> tuple[int, int, int, int]:
        modified = untracked = deleted = renamed = 0
        if not repo:
            return modified, untracked, deleted, renamed
        try:
            r = subprocess.run(
                ['git', '-C', repo, 'status', '--porcelain=v1', '-z',
                 '--untracked-files=normal'],
                capture_output=True, text=True, timeout=2,
            )
        except Exception:
            return modified, untracked, deleted, renamed
        entries = [e for e in r.stdout.split('\0') if e]
        i = 0
        while i < len(entries):
            entry = entries[i]
            if len(entry) < 2:
                i += 1
                continue
            x, y = entry[0], entry[1]
            if x == 'R' or y == 'R':
                renamed += 1
                i += 2  # rename consumes a second NUL-separated original-name field
                continue
            if x == '?' and y == '?':
                untracked += 1
            elif x == 'A' or y == 'A':
                untracked += 1
            elif x == 'D' or y == 'D':
                deleted += 1
            elif x == 'M' or y == 'M':
                modified += 1
            i += 1
        return modified, untracked, deleted, renamed


@dataclass
class LoadedSkills:
    names: list[str] = field(default_factory=list)

    @classmethod
    def from_transcript(cls, transcript_path: str) -> LoadedSkills:
        if not transcript_path:
            return cls()
        p = Path(transcript_path)
        if not p.is_file():
            return cls()
        skill_pat = re.compile(r'"name"\s*:\s*"Skill"[^}]*?"skill"\s*:\s*"([^"]+)"')
        read_pat = re.compile(r'"name"\s*:\s*"Read"[^}]*?"file_path"\s*:\s*"([^"]+)"')
        skill_path_pat = re.compile(r'/skills/([^/"]+)/SKILL\.md$')
        seen: dict[str, None] = {}
        try:
            with p.open('r', errors='ignore') as fh:
                for ln in fh:
                    if '"Skill"' in ln:
                        for m in skill_pat.finditer(ln):
                            name = m.group(1)
                            if name not in seen:
                                seen[name] = None
                    if '"Read"' in ln and 'SKILL.md' in ln:
                        for m in read_pat.finditer(ln):
                            sm = skill_path_pat.search(m.group(1))
                            if sm:
                                name = sm.group(1)
                                if name not in seen:
                                    seen[name] = None
        except OSError:
            return cls()
        return cls(names=list(seen.keys()))


@dataclass
class RunningSubagent:
    agent_type: str
    description: str
    billed_in: int
    output: int
    first_timestamp: float  # epoch seconds; baseline for live duration
    model:         str                   = ''
    cache_read_in: int                   = 0
    total_input:   int                   = 0
    last_activity: tuple[str, str, dict] = field(default_factory=lambda: ('', '', {}))


@dataclass
class RunningSubagents:
    subagents: list[RunningSubagent] = field(default_factory=list)

    STALE_SECONDS = 20

    @classmethod
    def from_session(cls, session_id: str, project_dir: str) -> RunningSubagents:
        if not session_id or not project_dir:
            return cls()
        # Match Claude Code's projects/ dir convention: replace every non-
        # alphanumeric character with '-'. Works on both Unix
        # ('/home/user/my-project' -> '-home-user-my-project') and Windows
        # ('C:\\Users\\desal\\Project' -> 'C--Users-desal-Project'). The old
        # logic was Unix-only because it normalized only '/' and relied on a
        # leading slash producing the '-' prefix that Claude Code uses on
        # Unix; on Windows paths start with a drive letter (no leading '-'
        # in CC's dir name) so the f-string prefix gave a wrong path.
        project_slug = re.sub(r'[^A-Za-z0-9]', '-', project_dir)
        subagents_dir = CLAUDE_DIR / 'projects' / project_slug / session_id / 'subagents'
        if not subagents_dir.is_dir():
            return cls()
        now = time.time()
        subagents: list[RunningSubagent] = []
        try:
            for meta in subagents_dir.glob('*.meta.json'):
                agent_type = ''
                description = ''
                try:
                    data = json.loads(meta.read_text())
                    agent_type = data.get('agentType', '')
                    description = data.get('description', '')
                except Exception:
                    continue

                jsonl = meta.with_suffix('').with_suffix('.jsonl')
                if not jsonl.is_file():
                    continue
                try:
                    mtime = jsonl.stat().st_mtime
                    if now - mtime > cls.STALE_SECONDS:
                        continue
                except OSError:
                    continue

                billed_in, cache_read_in, output, first_ts, model, last_activity = cls._parse_transcript(jsonl)
                subagents.append(RunningSubagent(
                    agent_type      = agent_type,
                    description     = description,
                    billed_in       = billed_in,
                    output          = output,
                    first_timestamp = first_ts,
                    model           = model,
                    cache_read_in   = cache_read_in,
                    total_input     = billed_in + cache_read_in,
                    last_activity   = last_activity,
                ))
        except OSError:
            pass
        subagents.sort(key=lambda s: s.first_timestamp)
        return cls(subagents=subagents)

    @staticmethod
    def _parse_transcript(jsonl: Path) -> tuple[int, int, int, float, str, tuple[str, str, dict]]:
        seen: set[str] = set()
        billed_in    = 0
        cache_read_in = 0
        output       = 0
        first_ts     = 0.0
        model        = ''
        last_activity: tuple[str, str, dict] = ('', '', {})
        try:
            with jsonl.open('r', errors='ignore') as fh:
                for ln in fh:
                    if first_ts == 0.0 and '"timestamp"' in ln:
                        try:
                            d = json.loads(ln)
                            ts = d.get('timestamp', '')
                            if ts:
                                first_ts = _parse_iso_to_epoch(ts)
                        except (ValueError, TypeError):
                            pass
                    if '"usage"' not in ln or '"assistant"' not in ln:
                        continue
                    try:
                        d = json.loads(ln)
                    except (ValueError, TypeError):
                        continue
                    msg = d.get('message') or {}
                    mid = msg.get('id')
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    if not model:
                        m = msg.get('model') or ''
                        if m:
                            model = m
                    u = msg.get('usage') or {}
                    billed_in     += (u.get('input_tokens', 0) or 0) + (u.get('cache_creation_input_tokens', 0) or 0)
                    cache_read_in += u.get('cache_read_input_tokens', 0) or 0
                    output        += u.get('output_tokens', 0) or 0
                    content = msg.get('content') or []
                    if content:
                        item = content[-1]
                        kind = item.get('type', '')
                        if kind == 'tool_use':
                            last_activity = ('tool_use', item.get('name', ''), item.get('input') or {})
                        elif kind == 'thinking':
                            last_activity = ('thinking', '', {})
                        elif kind == 'text':
                            last_activity = ('text', '', {})
        except OSError:
            pass
        return billed_in, cache_read_in, output, first_ts, model, last_activity


def _parse_iso_to_epoch(ts: str) -> float:
    try:
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        return datetime.fromisoformat(ts).timestamp()
    except (ValueError, TypeError):
        return 0.0


@dataclass
class Task:
    id: int
    subject: str
    active_form: str
    status: str  # 'pending' | 'in_progress' | 'completed'


@dataclass
class TaskList:
    tasks: list[Task] = field(default_factory=list)
    last_event_ts: float = 0.0

    FRESHNESS_CAP = 120.0  # 2 min — see docs/adr/0004
    GRACE_SECONDS = 20.0   # matches RunningSubagents.STALE_SECONDS

    @classmethod
    def from_session(cls, transcript_path: str) -> TaskList:
        if not transcript_path:
            return cls()
        path = Path(transcript_path)
        if not path.is_file():
            return cls()
        by_id: dict[int, Task] = {}
        next_id = 1
        last_ts = 0.0
        try:
            with path.open('r', errors='ignore') as fh:
                for ln in fh:
                    if '"TaskCreate"' not in ln and '"TaskUpdate"' not in ln:
                        continue
                    try:
                        d = json.loads(ln)
                    except ValueError:
                        continue
                    ts = _parse_iso_to_epoch(d.get('timestamp', ''))
                    content = d.get('message', {}).get('content', [])
                    if not isinstance(content, list):
                        continue
                    for c in content:
                        if not isinstance(c, dict) or c.get('type') != 'tool_use':
                            continue
                        name = c.get('name', '')
                        inp  = c.get('input') or {}
                        if name == 'TaskCreate':
                            subj = inp.get('subject', '') or ''
                            af   = inp.get('activeForm', '') or subj
                            by_id[next_id] = Task(id=next_id, subject=subj, active_form=af, status='pending')
                            next_id += 1
                            if ts > last_ts: last_ts = ts
                        elif name == 'TaskUpdate':
                            try:
                                tid = int(inp.get('taskId', '0'))
                            except (TypeError, ValueError):
                                continue
                            t = by_id.get(tid)
                            if not t:
                                continue
                            new_status = inp.get('status')
                            if new_status in ('pending', 'in_progress', 'completed'):
                                t.status = new_status
                            if 'activeForm' in inp and inp['activeForm']:
                                t.active_form = inp['activeForm']
                            if 'subject' in inp and inp['subject']:
                                t.subject = inp['subject']
                            if ts > last_ts: last_ts = ts
        except OSError:
            return cls()
        tasks = [by_id[k] for k in sorted(by_id.keys())]
        return cls(tasks=tasks, last_event_ts=last_ts)

    @property
    def total(self) -> int:
        return len(self.tasks)

    @property
    def completed(self) -> int:
        return sum(1 for t in self.tasks if t.status == 'completed')

    @property
    def active(self) -> Task | None:
        for t in reversed(self.tasks):
            if t.status == 'in_progress':
                return t
        return None

    @property
    def next_pending(self) -> Task | None:
        for t in self.tasks:
            if t.status == 'pending':
                return t
        return None

    def is_visible(self, now: float | None = None) -> bool:
        if not self.tasks or self.last_event_ts <= 0:
            return False
        if now is None:
            now = time.time()
        age = now - self.last_event_ts
        if age > self.FRESHNESS_CAP:
            return False
        if self.completed == self.total:
            return age <= self.GRACE_SECONDS
        return True


@dataclass
class TranscriptUsage:
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0

    @classmethod
    def from_transcript(cls, transcript_path: str) -> TranscriptUsage:
        if not transcript_path:
            return cls()
        p = Path(transcript_path)
        if not p.is_file():
            return cls()
        seen: set[str] = set()
        ti = cc = cr = to = 0
        try:
            with p.open('r', errors='ignore') as fh:
                for ln in fh:
                    if '"usage"' not in ln or '"assistant"' not in ln:
                        continue
                    try:
                        d = json.loads(ln)
                    except (ValueError, TypeError):
                        continue
                    msg = d.get('message') or {}
                    mid = msg.get('id')
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    u = msg.get('usage') or {}
                    ti += u.get('input_tokens', 0) or 0
                    cc += u.get('cache_creation_input_tokens', 0) or 0
                    cr += u.get('cache_read_input_tokens', 0) or 0
                    to += u.get('output_tokens', 0) or 0
        except OSError:
            return cls()
        return cls(
            input_tokens                = ti,
            cache_creation_input_tokens = cc,
            cache_read_input_tokens     = cr,
            output_tokens               = to,
        )

    @property
    def billed_in(self) -> int:
        return self.input_tokens + self.cache_creation_input_tokens

    @property
    def cache_read(self) -> int:
        return self.cache_read_input_tokens

    @property
    def out(self) -> int:
        return self.output_tokens


@dataclass
class OpenSpec:
    changes: list[tuple[str, int, int]] = field(default_factory=list)

    @classmethod
    def from_cwd(cls, cwd: str) -> OpenSpec:
        root = cls._find_root(cwd)
        if not root:
            return cls()
        out: list[tuple[str, int, int]] = []
        open_re = re.compile(r'^\s*- \[ \]')
        done_re = re.compile(r'^\s*- \[x\]')
        for tasks in sorted(Path(root).rglob('tasks.md')):
            if '/archive/' in str(tasks):
                continue
            try:
                text = tasks.read_text()
            except OSError:
                continue
            t = sum(1 for ln in text.splitlines() if open_re.match(ln))
            d = sum(1 for ln in text.splitlines() if done_re.match(ln))
            total = t + d
            if total == 0:
                continue
            out.append((tasks.parent.name, d, total))
        return cls(changes=out)

    @staticmethod
    def _find_root(cwd: str) -> str:
        curr = Path(cwd) if cwd else None
        while curr:
            if (curr / 'openspec').is_dir():
                return str(curr / 'openspec')
            if curr == curr.parent:
                break
            curr = curr.parent
        return ''


def sparkline_width(terminal_width: int) -> int:
    if terminal_width >= 130:
        return 30
    if terminal_width >= 110:
        return 20
    if terminal_width >= 90:
        return 10
    return 0


def fmt_tok(n: int) -> str:
    # Promote at the rounding boundary (>= 999.95 rounds to 1000.0 at .1f) so the
    # result never exceeds 6 visible chars ("999.9B") and stays within the token
    # column budget (IN_W/CACHE_W/OUT_W = 6). Without the billions tier, a
    # multi-billion day total renders as "4660.5M" (7 chars) and pushes that
    # row's dividers one cell out of alignment.
    if n >= 999_950_000:
        return f'{n/1_000_000_000:.1f}B'
    if n >= 999_950:
        return f'{n/1_000_000:.1f}M'
    if n >= 1000:
        return f'{n/1000:.1f}K'
    return str(n)


def fmt_dur(seconds: float) -> str:
    s = int(seconds)
    if s < 0:
        s = 0
    if s < 60:
        return f'{s}s'
    if s < 3600:
        return f'{s // 60}m{s % 60:02d}s'
    return f'{s // 3600}h{(s % 3600) // 60:02d}m'


RAINBOW_PALETTE = (
    196, 202, 208, 214, 220, 226, 190, 154, 118, 82,
    46, 47, 48, 49, 50, 51, 45, 39, 33, 27,
    21, 57, 93, 129, 165, 201, 200, 199, 198, 197,
)


def rainbow_step() -> int:
    return int(time.time()) % len(RAINBOW_PALETTE)


def rainbow_at(step: int, offset: int = 0) -> str:
    color = RAINBOW_PALETTE[(step + offset) % len(RAINBOW_PALETTE)]
    return f'\033[38;5;{color}m'


def rainbow_color() -> str:
    return rainbow_at(rainbow_step())


def model_key(name: str) -> str:
    m = name.lower()
    if 'opus'   in m: return 'opus'
    if 'sonnet' in m: return 'sonnet'
    if 'haiku'  in m: return 'haiku'
    return 'other'


class GradientEngine:
    FADE        = 0.06
    SPARK_CHARS = '▁▂▃▄▅▆▇█'

    def __init__(self, theme: Theme | None = None) -> None:
        t = theme if theme is not None else CLAUDE_DARK
        self.theme       = t
        self.GRAD_STOPS  = t.grad_stops
        self.GREY_RGB    = t.grey_rgb
        self.SPARK_STOPS = t.spark_stops
        self.BORDER_OFF  = t.border_off

    def spark_rgb(self, t: float, dim: float = 1.0) -> tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        for i in range(len(self.SPARK_STOPS) - 1):
            t0, c0 = self.SPARK_STOPS[i]
            t1, c1 = self.SPARK_STOPS[i + 1]
            if t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                r = int((c0[0] + (c1[0] - c0[0]) * u) * dim)
                g = int((c0[1] + (c1[1] - c0[1]) * u) * dim)
                b = int((c0[2] + (c1[2] - c0[2]) * u) * dim)
                return r, g, b
        r, g, b = self.SPARK_STOPS[-1][1]
        return int(r * dim), int(g * dim), int(b * dim)

    def spark_color(self, t: float, dim: float = 1.0) -> str:
        r, g, b = self.spark_rgb(t, dim)
        return f'\033[38;2;{r};{g};{b}m'

    def gradient_rgb(self, t: float, dim: float = 1.0) -> tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        for i in range(len(self.GRAD_STOPS) - 1):
            t0, c0 = self.GRAD_STOPS[i]
            t1, c1 = self.GRAD_STOPS[i + 1]
            if t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                r = int((c0[0] + (c1[0] - c0[0]) * u) * dim)
                g = int((c0[1] + (c1[1] - c0[1]) * u) * dim)
                b = int((c0[2] + (c1[2] - c0[2]) * u) * dim)
                return r, g, b
        r, g, b = self.GRAD_STOPS[-1][1]
        return int(r * dim), int(g * dim), int(b * dim)

    def gradient_color(self, t: float, dim: float = 1.0) -> str:
        r, g, b = self.gradient_rgb(t, dim)
        return f'\033[38;2;{r};{g};{b}m'

    def grad_at(self, col: int, width: int, dim: float = 1.0, fill: float = 1.0) -> str:
        denom = max(1, width - 1)
        t = col / denom
        if fill <= 0:
            return self.BORDER_OFF
        fade = self.FADE
        if t <= fill - fade:
            return self.gradient_color(t, dim)
        if t >= fill + fade:
            return self.BORDER_OFF
        er, eg, eb = self.gradient_rgb(min(t, fill), dim)
        gr, gg, gb = self.GREY_RGB
        u = max(0.0, min(1.0, (t - (fill - fade)) / (2 * fade)))
        r = int(er + (gr - er) * u)
        g = int(eg + (gg - eg) * u)
        b = int(eb + (gb - eb) * u)
        return f'\033[38;2;{r};{g};{b}m'

    def gradient_bar(self, filled: int, bar_w: int) -> str:
        if filled <= 0 or bar_w <= 0:
            return ''
        denom = max(1, bar_w - 1)
        parts = []
        for i in range(filled):
            r, g, b = self.gradient_rgb(i / denom)
            parts.append(f'\033[48;2;{r};{g};{b}m ')
        if filled <= bar_w:
            parts.append(f'\033[49m{self.gradient_color(filled / denom)}{BarChars.MID}')
        return ''.join(parts)

    def _spark_flat(self, idx: int) -> tuple[str, str]:
        if idx <= 0:
            return ' ', self.SPARK_CHARS[0]
        if idx <= 8:
            return ' ', self.SPARK_CHARS[idx - 1]
        return self.SPARK_CHARS[idx - 9], '█'

    def _spark_rise(self, idx: int) -> tuple[str, str]:
        if idx <= 0:
            return ' ', self.SPARK_CHARS[0]
        if idx <= 3:
            return ' ', SPARK_RISE_SMALL
        if idx <= 7:
            return ' ', SPARK_RISE_MED
        if idx <= 8:
            return ' ', SPARK_RISE_TALL
        return SPARK_RISE_TOP, SPARK_RISE_TALL

    def _spark_fall(self, idx: int) -> tuple[str, str]:
        if idx <= 0:
            return ' ', self.SPARK_CHARS[0]
        if idx <= 3:
            return ' ', SPARK_FALL_SMALL
        if idx <= 7:
            return ' ', SPARK_FALL_MED
        if idx <= 8:
            return ' ', SPARK_FALL_TALL
        return SPARK_FALL_TOP, SPARK_FALL_TALL

    def sparkline(self, history: list[int], live: bool = False) -> tuple[str, str]:
        if not history:
            return '', ''
        max_val = max(history)
        indices = [
            min(int(((v / max_val) if max_val > 0 else 0.0) * 16), 16)
            for v in history
        ]
        last_i  = len(indices) - 1
        top_parts = []
        bot_parts = []
        for i, idx in enumerate(indices):
            prev_idx = indices[i - 1] if i > 0 else 0
            if idx > prev_idx:
                top_ch, bot_ch = self._spark_rise(idx)
                tint_idx       = idx
            elif prev_idx > idx:
                top_ch, bot_ch = self._spark_fall(prev_idx)
                tint_idx       = prev_idx
            else:
                top_ch, bot_ch = self._spark_flat(idx)
                tint_idx       = idx
            ratio     = tint_idx / 16.0
            ratio_bot = ratio * 0.5
            ratio_top = 0.5 + ratio * 0.5
            if live and i == last_i:
                bot_clr = self.spark_color(ratio_bot, dim=LIVE_DIM)
                top_clr = self.spark_color(ratio_top, dim=LIVE_DIM)
            else:
                bot_clr = self.spark_color(ratio_bot)
                top_clr = self.spark_color(ratio_top)
            top_parts.append(f'{top_clr}{top_ch}{RESET}')
            bot_parts.append(f'{bot_clr}{bot_ch}{RESET}')
        return ''.join(top_parts), ''.join(bot_parts)


class BorderRenderer:
    def __init__(self, gradient: GradientEngine):
        self.gradient   = gradient
        self.SESSION    = gradient.theme.white_brt  # session label → bright white

    R = RESET

    def border_top(self, width: int, session_id: str = '', downs: tuple[int, ...] = (), fill: float = 1.0) -> str:
        downs_set = set(downs)
        def _ch(col: int) -> str:
            return '┬' if col in downs_set else '─'
        def _clr(col: int, pos: int) -> str:
            return self.gradient.grad_at(pos, width, fill=fill)
        parts = [self.gradient.grad_at(0, width, fill=fill), '╭']
        if session_id:
            # ╭ + 2 lead dashes + label + 1 gap column + ╮
            avail = max(0, width - 5)
            sid = _truncate_visible(session_id, avail)
            sid_w = _visible_width(sid)
            glyph_prefix = f'{GLYPH_SESSION_NAME} '
            if sid.startswith(glyph_prefix):
                rest = sid[len(GLYPH_SESSION_NAME):]
                parts += [_clr(2, 1), _ch(2), _clr(3, 2), _ch(3),
                          SESSION_NAME_GLYPH_FG, GLYPH_SESSION_NAME,
                          self.SESSION, ITALIC, rest, '\033[23m']
            else:
                parts += [_clr(2, 1), _ch(2), _clr(3, 2), _ch(3), self.SESSION, ITALIC, sid, '\033[23m']
            # A space between the label and the rule so the path doesn't butt
            # straight into the border.
            parts.append(' ')
            offset = 4 + sid_w
            rest = max(0, width - 5 - sid_w)
            for i in range(rest):
                col = offset + i + 1
                parts += [_clr(col, offset + i), _ch(col)]
        else:
            for i in range(1, width - 1):
                col = i + 1
                parts += [_clr(col, i), _ch(col)]
        parts += [self.gradient.grad_at(width - 1, width, fill=fill), '╮', self.R]
        return ''.join(parts)

    def border_bottom(self, width: int, ups: tuple[int, ...] = (), fill: float = 1.0) -> str:
        ups_set = set(ups)
        parts = [self.gradient.grad_at(0, width, fill=fill), '╰']
        for i in range(width - 2):
            ch = '┴' if (i + 2) in ups_set else '─'
            parts += [self.gradient.grad_at(i + 1, width, fill=fill), ch]
        parts += [self.gradient.grad_at(width - 1, width, fill=fill), '╯', self.R]
        return ''.join(parts)

    def border_separator(self, width: int, ups: tuple[int, ...] = (), fill: float = 1.0) -> str:
        ups_set = set(ups)
        parts = [self.gradient.grad_at(0, width, fill=fill), '├']
        for i in range(width - 2):
            ch = '┴' if (i + 2) in ups_set else '─'
            parts += [self.gradient.grad_at(i + 1, width, fill=fill), ch]
        parts += [self.gradient.grad_at(width - 1, width, fill=fill), '┤', self.R]
        return ''.join(parts)

    DIM_MIN  = 0.6
    DIM_RAMP = 5

    def _dim_for_col(self, col: int, elbow_cols: set[int]) -> float:
        d = min(abs(col - e) for e in elbow_cols)
        if d == 0:
            return 1.0
        return max(self.DIM_MIN, 1.0 - (1.0 - self.DIM_MIN) * (d / self.DIM_RAMP))

    def border_separator_dim(self, width: int, downs: tuple[int, ...] = (), ups: tuple[int, ...] = (), fill: float = 1.0) -> str:
        downs_set = set(downs)
        ups_set = set(ups)
        elbow_cols = {1, width} | downs_set | ups_set
        parts = [self.gradient.grad_at(0, width, self._dim_for_col(1, elbow_cols), fill=fill), '├']
        for i in range(width - 2):
            col = i + 2
            if col in downs_set and col in ups_set:
                ch = '┼'
            elif col in downs_set:
                ch = '┬'
            elif col in ups_set:
                ch = '┴'
            else:
                ch = '┄'
            parts += [self.gradient.grad_at(i + 1, width, self._dim_for_col(col, elbow_cols), fill=fill), ch]
        parts += [self.gradient.grad_at(width - 1, width, self._dim_for_col(width, elbow_cols), fill=fill), '┤', self.R]
        return ''.join(parts)

    def border_line(self, content: str, width: int, fill: float = 1.0) -> str:
        pad   = max(0, width - 3 - _visible_width(content))
        left  = self.gradient.grad_at(0, width, fill=fill)
        right = self.gradient.grad_at(width - 1, width, fill=fill)
        return f'{left}│{self.R} {content}{" " * pad}{right}│{self.R}'


class Renderer:
    def __init__(self, theme: Theme | None = None) -> None:
        self.theme    = theme if theme is not None else CLAUDE_DARK
        self.gradient = GradientEngine(self.theme)
        self.border   = BorderRenderer(self.gradient)
        self._apply_theme(self.theme)

    def _apply_theme(self, t: Theme) -> None:
        self.BORDER      = t.border
        self.PWD         = t.pwd
        self.BRANCH      = t.branch
        self.COMMIT      = t.commit
        self.SESSION     = t.session
        self.MODEL       = t.model
        self.SKILLS      = t.skills
        self.TIME        = t.time
        self.TOK         = t.tok
        self.TOK_DIM     = t.tok_dim
        self.TOK_DAY     = t.tok_day
        self.TOK_DAY_DIM = t.tok_day_dim
        self.COST        = t.cost
        self.BAR_FILL    = t.bar_fill
        self.BAR_EMPTY   = t.bar_empty
        self.DIM_GREEN   = t.dim_green
        self.LABEL       = t.label
        self.CTX         = t.ctx
        self.CTX_DIM     = t.ctx_dim
        self.BOLDW       = BOLD + t.white_brt
        self.BOLDY       = t.tok_arrow
        self.DIRTY       = t.dirty
        self.ICON_PATH   = t.icon_path
        self.ARROW       = t.arrow
        self.TOK_ICON    = t.tok_icon
        self.OPUS        = t.models['opus'].label
        self.SONNET      = t.models['sonnet'].label
        self.HAIKU       = t.models['haiku'].label
        self.safe        = t.safe
        self.warn        = t.warn
        self.alert       = t.alert
        self.yellow      = t.yellow
        self.white_brt   = t.white_brt
        self.SPEC_GRADIENTS  = t.spec_gradients
        self.spec_empty_ansi = t.spec_empty_ansi

    R         = RESET
    BORDER    = CLR_GREY_DIM
    PWD       = CLR_SKY_BLUE
    BRANCH    = CLR_GREEN_OK
    COMMIT    = CLR_GREY_DIM
    SESSION   = CLR_GREY_DIM
    MODEL     = CLR_PURPLE
    SKILLS    = CLR_GOLD
    TIME      = CLR_GREY_DIM
    TOK       = CLR_CYAN
    TOK_DIM   = CLR_CYAN_DIM
    TOK_DAY     = CLR_CYAN_DAY
    TOK_DAY_DIM = CLR_CYAN_DAY_DIM
    COST      = CLR_PINK
    BAR_FILL  = CLR_GREEN_OK
    BAR_EMPTY = CLR_GREY_DARK
    DIM_GREEN = CLR_GREEN_DIM
    LABEL     = CLR_GREY_DIM
    CTX       = CLR_PEACH
    CTX_DIM   = CLR_PEACH
    BOLDW     = BOLD + CLR_WHITE_BRT
    BOLDY     = CLR_YELLOW
    DIRTY     = CLR_WARN
    ICON_PATH = CLR_CYAN_ICON
    ARROW     = CLR_GREEN_BRT
    TOK_ICON  = CLR_YELLOW_BRT
    OPUS      = CLR_YELLOW
    SONNET    = CLR_GREEN_OK
    HAIKU     = CLR_SKY_BLUE

    # --- Gradient delegations (backward compat) ---
    # GRAD_STOPS / GREY_RGB / SPARK_STOPS now live on the GradientEngine
    # instance (driven by the active Theme). The legacy class-level constants
    # are gone; callers reach them via r.gradient.GRAD_STOPS etc.
    FADE        = GradientEngine.FADE
    SPARK_CHARS = GradientEngine.SPARK_CHARS

    def gradient_rgb(self, t: float, dim: float = 1.0) -> tuple[int, int, int]:
        return self.gradient.gradient_rgb(t, dim)

    def gradient_color(self, t: float, dim: float = 1.0) -> str:
        return self.gradient.gradient_color(t, dim)

    def grad_at(self, col: int, width: int, dim: float = 1.0, fill: float = 1.0) -> str:
        return self.gradient.grad_at(col, width, dim, fill)

    def gradient_bar(self, filled: int, bar_w: int) -> str:
        return self.gradient.gradient_bar(filled, bar_w)

    def vsep_block(self, col: int, width: int, fill: float = 1.0, *, leader: bool = False) -> str:
        color    = self.gradient.grad_at(col - 1, width, fill=fill)
        trailing = ' ' if leader else '  '
        return f'  {color}│{self.R}{trailing}'

    def sparkline(self, history: list[int], live: bool = False) -> tuple[str, str]:
        return self.gradient.sparkline(history, live)

    def spark_rgb(self, t: float, dim: float = 1.0) -> tuple[int, int, int]:
        return self.gradient.spark_rgb(t, dim)

    def spark_color(self, t: float, dim: float = 1.0) -> str:
        return self.gradient.spark_color(t, dim)

    # --- Border delegations (backward compat) ---
    def border_top(self, width: int, session_id: str = '', downs: tuple[int, ...] = (), fill: float = 1.0) -> str:
        return self.border.border_top(width, session_id, downs, fill)

    def border_bottom(self, width: int, ups: tuple[int, ...] = (), fill: float = 1.0) -> str:
        return self.border.border_bottom(width, ups, fill)

    def border_separator(self, width: int, ups: tuple[int, ...] = (), fill: float = 1.0) -> str:
        return self.border.border_separator(width, ups, fill)

    def border_separator_dim(self, width: int, downs: tuple[int, ...] = (), ups: tuple[int, ...] = (), fill: float = 1.0) -> str:
        return self.border.border_separator_dim(width, downs, ups, fill)

    def border_line(self, content: str, width: int, fill: float = 1.0) -> str:
        return self.border.border_line(content, width, fill)

    def activity_segment(self, activity: ActivityState) -> str:
        if activity.is_working:
            return f' {self.safe}{GLYPH_WORKING}{self.R} {self.safe}working{self.R}'
        return f' {self.LABEL}{GLYPH_IDLE} idle{self.R}'

    def path_git(
        self, short_pwd: str, git: GitInfo, elapsed: str = '', pr: Pr | None = None,
        *, show_commit: bool = True, show_dirty: bool = True, show_elapsed: bool = True,
        show_pr: bool = True, show_path: bool = True,
    ) -> str:
        dirty = ''
        if show_dirty:
            if git.untracked > 0:
                dirty += f'{self.DIRTY}•{git.untracked}{RESET}'
            if git.modified > 0:
                dirty += f'{self.DIRTY}*{git.modified}{RESET}'
            if git.deleted > 0:
                dirty += f'{self.DIRTY}-{git.deleted}{RESET}'
            if git.renamed > 0:
                dirty += f'{self.DIRTY}{GLYPH_RENAMED} {git.renamed}{RESET}'
            if dirty:
                dirty = ' ' + dirty
        tail = f' {self.SESSION}[{elapsed}]{self.R}' if (show_elapsed and elapsed and elapsed != '0m') else ''
        # '@' rather than '/': `feature/pdds/abc1234` reads as one path, and a
        # detached HEAD has no commit to separate at all.
        commit_part = f'{self.LABEL}@{self.R}{self.COMMIT}{git.commit}{self.R}' if (show_commit and git.commit) else ''
        pwd_text  = f'{self.PWD}{short_pwd}{self.R}'
        pwd_link  = osc8(git.remote_url, pwd_text)

        badge = self.pr_badge(pr) if show_pr else ''
        if not show_path:
            # The cwd lives in the top border; row 1 starts at the ref.
            return f'{self.ref_segment(git).lstrip()}{commit_part}{dirty}{badge}{tail}'
        return (
            f'{self.path_glyph(git)}  {pwd_link}'
            f'{self.ref_segment(git)}'
            f'{commit_part}{dirty}{badge}{tail}'
        )

    def ref_segment(self, git: GitInfo) -> str:
        """` <marker> <name>`, or '' outside a repo — a bare marker looks broken."""
        if not git.branch:
            return ''
        return f' {self.ref_marker(git)} {self.BRANCH}{self.ref_name(git)}{self.R}'

    # review_state → colour. Anything unrecognised keeps the neutral treatment.
    PR_STATE_COLOURS = {
        'approved':          'safe',
        'changes_requested': 'alert',
        'commented':         'yellow',
        'pending':           'CTX',
    }

    def pr_badge(self, pr: Pr | None) -> str:
        """`#1234` linked to the PR, coloured by review state. '' when no PR is open."""
        if pr is None or not pr.number:
            return ''
        slot   = self.PR_STATE_COLOURS.get(pr.review_state.lower(), 'LABEL')
        colour = getattr(self, slot)
        text   = f'{colour}{GLYPH_PR} #{pr.number}{self.R}'
        return ' ' + osc8(pr.url, text)

    def border_label(self, session_id: str, name: str, short_pwd: str,
                     git: GitInfo, budget: int) -> str:
        """Top-border label: `<tag> <name> | <id> | <glyph> <cwd>`, styled and fitted.

        The identity half is never sacrificed, and the cwd is never shortened:
        a clipped path is worse than no path, so when the whole thing doesn't
        fit it is dropped and row 1 keeps its own git detail regardless.
        """
        sid_short = short_session_id(session_id)
        sid_link  = osc8(resume_url(session_id), f'{self.SESSION}{ITALIC}{sid_short}{RESET}')
        ident_plain = f'{GLYPH_SESSION_NAME} {name} | {sid_short}' if name else sid_short
        ident = (
            f'{SESSION_NAME_GLYPH_FG}{GLYPH_SESSION_NAME}{self.R} '
            f'{self.SESSION}{ITALIC}{name}{RESET} {self.LABEL}|{self.R} '
            f'{sid_link}'
        ) if name else sid_link

        if not short_pwd:
            return ident
        # ' | ' + glyph + ' ' costs 5 columns before a single path char lands,
        # and border_top keeps one more for the gap before the rule resumes.
        path_budget = budget - _visible_width(ident_plain) - 6
        tail_only   = '/'.join(short_pwd.split('/')[-max(1, git.repo_tail):])
        for candidate in (
            short_pwd,
            abbreviate_ancestors(short_pwd, git.repo_tail),
            f'…/{tail_only}',
        ):
            if _visible_width(candidate) <= path_budget:
                pwd = candidate
                break
        else:
            return ident
        pwd_styled = osc8(git.remote_url, f'{self.PWD}{pwd}{self.R}')
        return f'{ident} {self.LABEL}|{self.R} {self.path_glyph(git)} {pwd_styled}'

    def path_glyph(self, git: GitInfo) -> str:
        """Leading glyph for the path: a fork when this checkout is a linked worktree."""
        if git.is_worktree:
            return f'{self.SKILLS}{GLYPH_WORKTREE}{self.R}'
        return f'{self.ICON_PATH}{GLYPH_FOLDER}{self.R}'

    @staticmethod
    def _detached(git: GitInfo) -> bool:
        return git.branch.startswith('d:')

    def ref_marker(self, git: GitInfo) -> str:
        """Glyph before the ref name — branch normally, commit on a detached HEAD."""
        glyph = GLYPH_COMMIT if self._detached(git) else GLYPH_BRANCH
        return f'{self.LABEL}{self.ARROW}{BOLD}{glyph}{self.R}'

    def ref_name(self, git: GitInfo) -> str:
        """Branch name, or the bare sha when detached (the glyph already says which)."""
        return git.branch[2:] if self._detached(git) else git.branch

    def path_git_compact(self, short_pwd: str, git: GitInfo) -> str:
        pwd_text = f'{self.PWD}{short_pwd}{self.R}'
        return f'{self.path_glyph(git)}  {osc8(git.remote_url, pwd_text)}{self.ref_segment(git)}'

    def fit_path(
        self, short_pwd: str, git: GitInfo, elapsed: str, target_w: int,
        pr: Pr | None = None, *, compact_only: bool = False, show_path: bool = True,
    ) -> str:
        def fits(s: str) -> bool:
            return _visible_width(s) <= target_w

        if not compact_only:
            for kwargs in (
                {},
                {'show_commit': False},
                {'show_commit': False, 'show_elapsed': False},
                {'show_commit': False, 'show_elapsed': False, 'show_pr': False},
                {'show_commit': False, 'show_elapsed': False, 'show_pr': False, 'show_dirty': False},
            ):
                candidate = self.path_git(short_pwd, git, elapsed, pr, show_path=show_path, **kwargs)
                if fits(candidate):
                    return candidate
        if not show_path:
            # Nothing left to shrink — the compact ladder below is all path work.
            return self.path_git(short_pwd, git, elapsed, pr, show_path=False,
                                 show_commit=False, show_elapsed=False,
                                 show_pr=False, show_dirty=False)

        compact = self.path_git_compact(short_pwd, git)
        if fits(compact):
            return compact

        # Ellipsis on short_pwd only
        for pwd_w in range(target_w - 1, 0, -1):
            trunc_pwd = _middle_ellipsis(short_pwd, pwd_w)
            candidate = self.path_git_compact(trunc_pwd, git)
            if fits(candidate):
                return candidate

        # Ellipsis on both short_pwd and branch
        # Overhead of path_git_compact with empty strings is 5 visible chars.
        half = max(1, (target_w - 5) // 2)
        trunc_pwd    = _middle_ellipsis(short_pwd,  half)
        trunc_branch = _middle_ellipsis(git.branch, half)
        truncated_git = GitInfo(
            branch=trunc_branch, commit=git.commit,
            modified=git.modified, untracked=git.untracked,
            deleted=git.deleted, renamed=git.renamed,
        )
        return self.path_git_compact(trunc_pwd, truncated_git)

    def model_colour(self, model_name: str) -> str:
        return self.theme.models[model_key(model_name)].label

    def fill_colour(self, pct: float) -> str:
        if pct >= 90:
            return self.alert
        if pct >= 70:
            return self.warn
        return self.safe

    def risk_zone_color(self, tokens: int) -> str:
        if tokens <= 50_000:
            return self.safe
        if tokens <= 80_000:
            return self.yellow
        if tokens <= 150_000:
            return self.warn
        return self.alert

    def day_cost_colour(self, cost: float) -> str:
        if cost > 50:
            return self.alert
        if cost >= 25:
            return self.yellow
        return self.safe

    def model_section_compact(self, model_name: str, rate_limits: RateLimits, max_width: int, effort_level: str = '') -> tuple[str, int]:
        model_clr = self.model_colour(model_name)
        pct       = rate_limits.five_hour.used_percentage or 0
        pct_clr   = self.fill_colour(float(pct))
        step      = rainbow_step()
        c_helper  = rainbow_at(step, 9)
        rate_pct  = f'{pct_clr}{pct}%{self.R}'

        rate_with_time = None
        try:
            if rate_limits.five_hour.resets_at:
                resets_at = datetime.fromtimestamp(rate_limits.five_hour.resets_at).astimezone()
                delta = resets_at - datetime.now().astimezone().replace(microsecond=0)
                if delta.total_seconds() > 0:
                    total_s = int(delta.total_seconds())
                    h, rem  = divmod(total_s, 3600)
                    m       = rem // 60
                    time_str       = f'{h}h{m}m' if h else f'{m}m'
                    rate_with_time = f'{rate_pct} {self.COMMIT}{time_str}{self.R}'
        except Exception:
            pass

        def _build(name: str, rate: str) -> tuple[str, int]:
            return (
                f'{model_clr}{GLYPH_MODEL}  {name}{self.R}'
                f' {self.LABEL}|{self.R}'
                f' {c_helper}{BOLD}{GLYPH_HELPER}{self.R} {rate}'
            ), 0

        if rate_with_time:
            line, pw = _build(model_name, rate_with_time)
            if _visible_width(line) <= max_width:
                return line, pw

        line, pw = _build(model_name, rate_pct)
        if _visible_width(line) <= max_width:
            return line, pw

        base_w      = _visible_width(_build('', rate_pct)[0])
        name_budget = max(3, max_width - base_w - 1)
        return _build(model_name[:name_budget] + '…', rate_pct)

    def monitors_segment(self, monitors: list[Monitor], now: float | None = None) -> str:
        if not monitors:
            return ''
        if now is None:
            now = time.time()
        parts = []
        for m in monitors:
            desc = m.description or '(no description)'
            elapsed = fmt_dur(max(0.0, now - m.started_at))
            parts.append(f'{self.ICON_PATH}{GLYPH_MONITOR}{self.R} {self.PWD}{desc}{self.R} {self.LABEL}·{self.R} {self.MODEL}{elapsed}{self.R}')
        sep = f' {self.LABEL}|{self.R} '
        return sep.join(parts)

    @staticmethod
    def _weekly_reset_str(resets_at: int, now: float | None = None) -> str:
        """Countdown to the 7-day bucket reset, coarsened to d/h/m. '' when unknown or past."""
        if not resets_at:
            return ''
        if now is None:
            now = time.time()
        total_s = int(resets_at - now)
        if total_s <= 0:
            return ''
        d, rem = divmod(total_s, 86400)
        h, rem = divmod(rem, 3600)
        m      = rem // 60
        if d:
            return f'{d}d{h}h'
        if h:
            return f'{h}h{m}m'
        return f'{m}m'

    def weekly_segment(self, seven_day: RateBucket) -> str:
        """Weekly (7-day) usage bucket: glyph + used % + time until the window resets."""
        pct = seven_day.used_percentage or 0
        if not pct and not seven_day.resets_at:
            return ''
        c_weekly = rainbow_at(rainbow_step(), 4)
        pct_clr  = self.fill_colour(float(pct))
        seg      = f'{c_weekly}{BOLD}{GLYPH_WEEKLY}{self.R} {pct_clr}{BOLD}{float(pct):.0f}%{self.R}'
        reset    = self._weekly_reset_str(seven_day.resets_at)
        if reset:
            seg += f' {self.COMMIT}{reset}{self.R}'
        return seg

    def model_right_section(self, model_name: str, model_thinking: str, rate_limits: RateLimits, effort_level: str = '', fast_mode: bool = False, monitors: list[Monitor] | None = None, activity: ActivityState | None = None, agent_name: str = '') -> tuple[str, str, int]:
        step      = rainbow_step()
        c_think   = rainbow_at(step, 0)
        c_helper  = rainbow_at(step, 9)
        model_clr = self.model_colour(model_name)
        glyph     = GLYPH_FAST if fast_mode else GLYPH_THINKING

        if model_thinking:
            right_text = f'{self.alert}{GLYPH_MODEL}{self.R}  {self.white_brt}{model_name}{self.R} {self.alert}{BOLD}{glyph}{self.R}  {self.white_brt}{ITALIC}{model_thinking}{RESET}'
        else:
            right_text = f'{self.alert}{GLYPH_MODEL}{self.R}  {self.white_brt}{model_name}{self.R}'

        if agent_name:
            right_text += f' {self.LABEL}·{self.R} {self.SKILLS}{agent_name}{self.R}'

        right_w = _visible_width(right_text)
        parts = []
        if activity is not None:
            parts.append(self.activity_segment(activity).lstrip())
        mons = self.monitors_segment(monitors or [])
        if mons:
            parts.append(mons)
        sep = f' {self.LABEL}|{self.R} '
        helper_text = sep.join(parts)
        return helper_text, right_text, right_w

    def model_right_section_compact(self, model_name: str, rate_limits: RateLimits, max_right_width: int, effort_level: str = '') -> tuple[str, str, int]:
        model_clr = self.model_colour(model_name)
        pct       = rate_limits.five_hour.used_percentage or 0
        pct_clr   = self.fill_colour(float(pct))
        rate_text = f'{pct_clr}{pct}%{self.R}'
        try:
            if rate_limits.five_hour.resets_at:
                resets_at = datetime.fromtimestamp(rate_limits.five_hour.resets_at).astimezone()
                delta = resets_at - datetime.now().astimezone().replace(microsecond=0)
                if delta.total_seconds() > 0:
                    total_s = int(delta.total_seconds())
                    h, rem  = divmod(total_s, 3600)
                    m       = rem // 60
                    time_str = f'{h}h{m}m' if h else f'{m}m'
                    rate_text = f'{rate_text} {self.COMMIT}{time_str}{self.R}'
        except Exception:
            pass

        def _make_right(name: str) -> tuple[str, int]:
            text = f'{model_clr}{GLYPH_MODEL}  {name}{self.R}'
            return text, _visible_width(text)

        right_text, right_w = _make_right(model_name)
        if right_w > max_right_width and max_right_width > 0:
            _, base_w = _make_right('')
            budget    = max(3, max_right_width - base_w - 1)
            right_text, right_w = _make_right(model_name[:budget] + '…')
        return rate_text, right_text, right_w

    def plugins_skills(self, skills_count: int, skills_names: str, plugin_names: str, budget: int = 0) -> str:
        step = rainbow_step()
        c_plugins = rainbow_at(step, 6)

        def _fit(items_str: str, avail: int) -> str:
            if avail <= 0 or _visible_width(items_str) <= avail:
                return items_str
            parts = items_str.split(',')
            kept: list[str] = []
            running = 0
            for p in parts:
                add = (1 if kept else 0) + _visible_width(p)
                if running + add + 1 > avail:  # +1 reserves space for '…'
                    break
                kept.append(p)
                running += add
            return (','.join(kept) + '…') if kept else '…'

        sep_w = 3  # ' | '
        glyph_w = 3  # glyph + 2 spaces
        extras_specs: list[tuple[str, str, str]] = []  # (color, glyph, names)
        if skills_count > 0:
            extras_specs.append((self.alert, GLYPH_SKILLS, skills_names))
        if plugin_names:
            extras_specs.append((c_plugins, GLYPH_PLUGINS, plugin_names))
        if not extras_specs:
            return ''

        if budget > 0:
            fixed = sum(glyph_w + _visible_width(n) for _, _, n in extras_specs) + sep_w * (len(extras_specs) - 1)
            if fixed > budget:
                # Shrink the names proportionally; plugins first since they're usually longer.
                remaining = budget - sep_w * (len(extras_specs) - 1) - glyph_w * len(extras_specs)
                remaining = max(0, remaining)
                # Distribute remaining width: give skills its natural width if possible, rest to plugins.
                shrunk: list[tuple[str, str, str]] = []
                if len(extras_specs) == 2:
                    skills_w = min(_visible_width(extras_specs[0][2]), max(0, remaining // 3))
                    plugins_w = max(0, remaining - skills_w)
                    shrunk.append((extras_specs[0][0], extras_specs[0][1], _fit(extras_specs[0][2], skills_w)))
                    shrunk.append((extras_specs[1][0], extras_specs[1][1], _fit(extras_specs[1][2], plugins_w)))
                else:
                    shrunk.append((extras_specs[0][0], extras_specs[0][1], _fit(extras_specs[0][2], remaining)))
                extras_specs = shrunk

        extras = [f'{c}{BOLD}{g}{self.R}  {self.white_brt}{n}{self.R}' for c, g, n in extras_specs if n]
        return f' {self.LABEL}|{self.R} '.join(extras)

    SUBAGENT_TOK_W = 6  # fmt_tok('999.9K') is 6 chars; reserve to avoid jitter

    def subagent_activity(self, last_activity: tuple[str, str, dict]) -> str:
        kind, name, inp = last_activity
        if kind == 'tool_use':
            key = TOOL_ARG_KEY.get(name)
            if key and key in inp:
                raw = str(inp[key])
                if key == 'file_path':
                    raw = Path(raw).name
            elif inp:
                raw = str(next(iter(inp.values())))
            else:
                raw = ''
            if _visible_width(raw) > 36:
                raw = raw[:36] + '…'  # U+2026 HORIZONTAL ELLIPSIS
            return f'{GLYPH_TASKS} {name}[{raw}]'
        if kind == 'thinking':
            return f'{GLYPH_THINKING} (thinking)'
        if kind == 'text':
            return f'{GLYPH_REPLYING} (replying)'
        return ''

    def subagent_row(self, sub: RunningSubagent, width: int) -> str:
        now     = time.time()
        dur     = max(0.0, now - sub.first_timestamp) if sub.first_timestamp > 0 else 0.0
        dur_s   = fmt_dur(dur).rjust(5)
        out_s   = fmt_tok(sub.output)
        tok_s   = fmt_tok(sub.total_input)

        short_model = model_key(sub.model)  # 'opus'/'sonnet'/'haiku'/'other'
        model_clr   = self.model_colour(sub.model)
        ctx_clr     = self.risk_zone_color(sub.total_input)
        cost        = TokenAccounting.session_cost(
            Model(id=sub.model),
            TranscriptUsage(
                input_tokens            = sub.billed_in,
                cache_read_input_tokens = sub.cache_read_in,
                output_tokens           = sub.output,
            ),
        )
        cost_s = f'{cost:.2f}'

        step     = rainbow_step()
        c_marker = rainbow_at(step, 12)
        type_text = sub.agent_type or '?'

        target_w = width - 4  # content width (2 for '│ ' left, 2 for ' │' right)

        if width > 100:
            # --- identity line (▶) ---
            right1 = (
                f'{model_clr}{short_model}{self.R}'
                f' {self.LABEL}·{self.R}'
                f' {self.LABEL}{BOLD}↑{self.R}{self.CTX}{out_s}{self.R}'
                f' {self.LABEL}·{self.R}'
                f' {self.CTX}{dur_s}{self.R}'
            )
            right1_w = _visible_width(right1)

            head1_w  = 3 + _visible_width(type_text) + 3  # '▶  ' + type + ' · '
            desc_budget = max(0, target_w - head1_w - 1 - right1_w)
            desc_text   = sub.description or ''
            if _visible_width(desc_text) > desc_budget:
                desc_text = (desc_text[:desc_budget - 1] + '…') if desc_budget > 0 else ''

            left1 = (
                f'{c_marker}{BOLD}{GLYPH_SUBAGENT_ROW}{self.R}  '
                f'{self.SKILLS}{type_text}{self.R}'
                f' {self.LABEL}·{self.R} '
                f'{self.CTX}{desc_text}{self.R}'
            )
            left1_w = head1_w + _visible_width(desc_text)
            pad1    = max(1, target_w - left1_w - right1_w)
            line1   = f'{left1}{" " * pad1}{right1}'

            # --- continuation line (└) ---
            right2 = (
                f'{ctx_clr}{GLYPH_HOURGLASS} {tok_s}{self.R}'
                f' {self.LABEL}·{self.R}'
                f' {self.COST}${cost_s}{self.R}'
            )
            right2_w = _visible_width(right2)

            activity   = self.subagent_activity(sub.last_activity)
            activity_w = _visible_width(activity)
            left2_w    = 6 + activity_w

            left2 = (
                f'   {self.CTX_DIM}{GLYPH_CONTINUATION}{self.R}  '
                f'{self.CTX_DIM}{activity}{self.R}'
            )
            pad2  = max(1, target_w - left2_w - right2_w)
            line2 = f'{left2}{" " * pad2}{right2}'

            return f'{line1}\n{line2}'

        else:
            # --- narrow single-line collapse ---
            kind = sub.last_activity[0]
            tool_verb = sub.last_activity[1] if kind == 'tool_use' else (
                '(thinking)' if kind == 'thinking' else
                '(replying)' if kind == 'text' else ''
            )

            right_n = (
                f'{ctx_clr}{GLYPH_HOURGLASS} {tok_s}{self.R}'
                f'  {self.COST}${cost_s}{self.R}'
                f'  {self.LABEL}{BOLD}↑{self.R}{self.CTX}{out_s}{self.R}'
                f'  {self.CTX}{dur_s}{self.R}'
            )
            right_n_w = _visible_width(right_n)

            left_n = (
                f'{c_marker}{BOLD}{GLYPH_SUBAGENT_ROW}{self.R}  '
                f'{self.SKILLS}{type_text}{self.R}'
                f'  {model_clr}{short_model}{self.R}'
                f'  {self.CTX}{tool_verb}{self.R}'
            )
            left_n_w = _visible_width(left_n)
            pad_n    = max(1, target_w - left_n_w - right_n_w)
            return f'{left_n}{" " * pad_n}{right_n}'

    def subagent_header(self, count: int) -> str:
        step    = rainbow_step()
        c_glyph = rainbow_at(step, 12)
        label   = 'subagents' if count != 1 else 'subagent'
        return (
            f'{c_glyph}{BOLD}{GLYPH_SUBAGENT}{self.R}  '
            f'{self.SKILLS}{count}{self.R} '
            f'{self.LABEL}{label}{self.R}'
        )

    def task_row(self, tasks: TaskList, width: int, compact: bool = False) -> str:
        step    = rainbow_step()
        c_glyph = rainbow_at(step, 9)
        done    = tasks.completed
        total   = tasks.total
        count_s = f'{done}/{total}'

        head = f'{c_glyph}{BOLD}{GLYPH_TASKS}{self.R}  {self.SKILLS}{count_s}{self.R}'
        if compact:
            return head

        if done == total:
            text = ''
        else:
            active = tasks.active
            if active is not None:
                text = active.active_form or active.subject
            else:
                nxt = tasks.next_pending
                text = nxt.subject if nxt else ''

        if not text:
            return head

        target_w = width - 4
        head_w   = 3 + len(count_s) + 2  # glyph + '  ' + count + '  '
        budget   = max(0, target_w - head_w)
        if len(text) > budget:
            text = (text[:budget - 1] + '…') if budget > 0 else ''
        return f'{head}  {self.CTX}{text}{self.R}'

    RATE_W  = 6
    IN_W    = 6
    CACHE_W = 6
    OUT_W   = 6

    def tokens_cost(self, sess_in: int, sess_cache: int, sess_out: int, day_in: int, day_cache: int, day_out: int, sess_cost: float, day_cost: float, tok_rate: int, session_id: str = '', box_width: int = 80, fill: float = 1.0) -> str:
        day_clr = self.day_cost_colour(day_cost)
        in_active, out_active = TokenRate.recently_active(session_id)
        in_icon  = '\U0001f847 ' if in_active  else '↓ '  # 🡇+space or ↓+space (both 2 cols)
        out_icon = '\U0001f845 ' if out_active else '↑ '  # 🡅+space or ↑+space (both 2 cols)

        sess_in_s    = fmt_tok(sess_in).rjust(self.IN_W)
        day_in_s     = fmt_tok(day_in).rjust(self.IN_W)
        sess_cache_s = fmt_tok(sess_cache).rjust(self.CACHE_W)
        day_cache_s  = fmt_tok(day_cache).rjust(self.CACHE_W)
        sess_out_s   = fmt_tok(sess_out).rjust(self.OUT_W)
        day_out_s    = fmt_tok(day_out).rjust(self.OUT_W)

        vsep_w        = 4
        vsep_leader_w = 4

        middle1 = f'{self.LABEL}{self.BOLDY}{in_icon}{self.R}{self.TOK}{sess_in_s}{self.R} {self.TOK_DIM}({sess_cache_s}){self.R}{self.LABEL} {self.BOLDY}{out_icon}{self.R}{self.TOK}{sess_out_s}{self.R}'
        middle2 = f'{self.LABEL}{self.BOLDY}{in_icon}{self.R}{self.TOK_DAY}{day_in_s}{self.R} {self.TOK_DAY_DIM}({day_cache_s}){self.R}{self.LABEL} {self.BOLDY}{out_icon}{self.R}{self.TOK_DAY}{day_out_s}{self.R}'

        cost1 = f'${sess_cost:,.2f}'
        cost2 = f'${day_cost:,.2f}'
        cost_width = max(_visible_width(cost1), _visible_width(cost2))

        end1 = f'{self.safe}{ICON_COST}{self.R} {self.COST}{cost1.rjust(cost_width)}{self.R}'
        end2 = f'  {self.LABEL}{self.R}{day_clr}{cost2.rjust(cost_width)}{self.R}'

        label_w = 15
        w_middle = _visible_width(middle1)
        w_end    = max(_visible_width(end1), _visible_width(end2))
        content_w = box_width - 3
        leader_w = max(label_w + 1, content_w - w_middle - w_end - vsep_w - vsep_leader_w)

        col1 = w_middle + 5                  # 1-indexed position of vsep │
        col2 = w_middle + vsep_w + w_end + 5  # 1-indexed position of vsep_leader │
        vsep        = self.vsep_block(col1, box_width, fill=fill, leader=True)
        vsep_leader = self.vsep_block(col2, box_width, fill=fill, leader=True)
        # bar_w = leader_w - label_w

        rate_label = f'{self.TOK_ICON}{ICON_TOK_RATE} {self.TOK}{fmt_tok(tok_rate)}{self.R}{self.LABEL} t/m{self.R}'
        rate_label_w = _visible_width(rate_label)
        rate_label_padded = f'{rate_label}' #{" " * max(0, label_w - rate_label_w)}'
        bar_w = leader_w - rate_label_w

        if bar_w <= 0:
            leader1 = rate_label_padded
            leader2 = ' ' * label_w
        else:
            if session_id:
                spark_history = TokenRate.history(session_id, bar_w, TokenRate.WINDOW * 2)
                top_row, bot_row = self.sparkline(spark_history[::-1], live=True)
            else:
                top_row, bot_row = ' ' * bar_w, ' ' * bar_w
            leader1 = f'{rate_label_padded}{top_row}'
            # leader2 = f'{" " * label_w}{bot_row}'
            leader2 = f'{" " * rate_label_w}{bot_row}'

        # 1-indexed column of the WINDOW (60s) tick inside the sparkline. History
        # spans WINDOW*2 (=120s) across bar_w buckets reversed so index 0 is "now",
        # which puts the 60s boundary at bar_w // 2. col2 is the vsep_leader │
        # column; sparkline starts rate_label_w cells past that.
        mark_col = col2 + rate_label_w + (bar_w // 2) if bar_w > 0 else 0

        return [
            f'{middle1}{vsep}{end1}{vsep_leader}{leader1}',
            f'{middle2}{vsep}{end2}{vsep_leader}{leader2}',
        ], (col1, col2), mark_col

    def context_bar(self, fill_ratio: float) -> str:
        ratio = min(max(fill_ratio, 0.0), 1.0)
        filled = int(ratio * 30)
        bar_filled = BarChars.FILLED * filled
        bar_empty = BarChars.EMPTY * (30 - filled)
        if ratio >= 0.9:
            color = self.alert
        elif ratio >= 0.7:
            color = self.warn
        else:
            color = self.safe
        return f'{color}{bar_filled}{self.R}{self.BAR_EMPTY}{bar_empty}{self.R}'

    def context_bar_color(self, fill_ratio: float) -> str:
        ratio = min(max(fill_ratio, 0.0), 1.0)
        if ratio >= 0.9:
            return self.alert
        elif ratio >= 0.7:
            return self.warn
        else:
            return self.safe

    _EMPTY_FADE_256 = re.compile(r'\x1b\[38;5;(\d+)m')
    _EMPTY_FADE_RGB = re.compile(r'\x1b\[38;2;(\d+);(\d+);(\d+)m')

    def _empty_fade_colors(self) -> list[str]:
        # 3-step ramp going from a darker shade up to BAR_EMPTY, so the fill→empty
        # seam blends instead of butting a coloured glyph against flat grey.
        m = self._EMPTY_FADE_256.search(self.BAR_EMPTY)
        if m:
            n = int(m.group(1))
            return [f'\033[38;5;{max(232, n - k)}m' for k in (6, 4, 2)]
        m = self._EMPTY_FADE_RGB.search(self.BAR_EMPTY)
        if m:
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return [f'\033[38;2;{int(r*k)};{int(g*k)};{int(b*k)}m' for k in (0.3, 0.5, 0.7)]
        return [self.BAR_EMPTY] * 3

    def _empty_section(self, empty: int, blend: bool = True) -> str:
        if empty <= 0:
            return ''
        if not blend:
            return f'{self.BAR_EMPTY}{BarChars.EMPTY * empty}'
        fade  = self._empty_fade_colors()
        n     = min(len(fade), empty)
        parts = [f'{fade[i]}{BarChars.EMPTY}' for i in range(n)]
        if empty > n:
            parts.append(f'{self.BAR_EMPTY}{BarChars.EMPTY * (empty - n)}')
        return ''.join(parts)

    def _window_used_pct(self, ctx: ContextWindow) -> float:
        """Actual window usage 0-100. Prefer the server-provided remaining_percentage."""
        if ctx.remaining_percentage is not None:
            return max(0.0, min(100.0, 100.0 - float(ctx.remaining_percentage)))
        if ctx.context_window_size > 0:
            total = ctx.total_input_tokens + ctx.total_output_tokens
            return max(0.0, min(100.0, total / ctx.context_window_size * 100))
        return 0.0

    def context_line(self, ctx: ContextWindow, available: int = 76,
                     cost: Cost | None = None) -> str:
        used_pct     = self._window_used_pct(ctx)
        total_tokens = ctx.total_input_tokens + ctx.total_output_tokens
        in_alert     = used_pct >= 90
        bar_clr      = self.fill_colour(used_pct)
        glyph        = GLYPH_WARNING if in_alert else GLYPH_HOURGLASS
        glyph_clr    = self.alert if in_alert else self.LABEL
        tok_part     = f'{self.LABEL}{fmt_tok(total_tokens)}{self.R} ' if total_tokens else ''
        line = f' {glyph_clr}{glyph}{self.R} {tok_part}{bar_clr}{BOLD}{used_pct:.0f}%{self.R}'
        return line + self.churn_segment(cost)

    def churn_segment(self, cost: Cost | None) -> str:
        """Lines this session added/removed — '' when nothing has changed yet."""
        if cost is None or not (cost.total_lines_added or cost.total_lines_removed):
            return ''
        return (f'  {self.safe}+{cost.total_lines_added}{self.R}'
                f'{self.LABEL}/{self.R}{self.DIRTY}-{cost.total_lines_removed}{self.R}')


    def context_line_compact(self, ctx: ContextWindow, available: int) -> str:
        used_pct = self._window_used_pct(ctx)
        bar_clr  = self.fill_colour(used_pct)
        return f' {bar_clr}{BOLD}{used_pct:.0f}%{self.R}'


    SPEC_GRADIENTS = [
        ((20, 60, 200),  (30, 200, 180),  (220, 255, 120)),     # Ocean    blue → teal → pale green
        ((60, 20, 160),  (240, 60, 140),  (255, 200, 60)),      # Sunset   indigo → magenta → gold
        ((10, 80, 120),  (120, 220, 40),  (240, 240, 60)),      # Forest   navy → lime → yellow
        ((80, 20, 200),  (240, 100, 220), (255, 200, 160)),     # Lavender purple → hot-pink → peach
        ((140, 20, 30),  (240, 120, 20),  (255, 230, 80)),      # Ember    dark-red → orange → yellow
        ((30, 40, 140),  (60, 200, 240),  (220, 240, 255)),     # Arctic   navy → cyan → white
        ((90, 30, 10),   (220, 120, 30),  (255, 220, 100)),     # Copper   brown → orange → gold
        ((160, 10, 50),  (240, 100, 160), (255, 220, 220)),     # Rose     wine → pink → cream
        ((10, 90, 100),  (60, 220, 160),  (220, 255, 180)),     # Mint     dark-teal → mint → pale-yellow
        ((40, 10, 140),  (220, 40, 200),  (60, 220, 240)),      # Nebula   violet → magenta → cyan
        ((140, 30, 200), (40, 180, 240),  (60, 230, 120)),      # Aurora   violet → cyan → green
        ((60, 0, 20),    (220, 60, 20),   (255, 220, 40)),      # Volcano  black-red → orange → yellow
    ]

    SPEC_MID_MIN_WIDTH = 20

    def _spec_rgb_at(self, t: float, idx: int, three_stops: bool = True) -> tuple[int, int, int]:
        stops = self.SPEC_GRADIENTS[idx % len(self.SPEC_GRADIENTS)]
        if not three_stops:
            stops = (stops[0], stops[-1])
        n = len(stops)
        seg = max(0.0, min(1.0, t)) * (n - 1)
        s0 = min(int(seg), n - 2)
        s1 = s0 + 1
        u = seg - s0
        c0, c1 = stops[s0], stops[s1]
        return (
            int(c0[0] + (c1[0] - c0[0]) * u),
            int(c0[1] + (c1[1] - c0[1]) * u),
            int(c0[2] + (c1[2] - c0[2]) * u),
        )

    def spec_gradient_bar(self, filled: int, bar_w: int, idx: int) -> str:
        if filled <= 0 or bar_w <= 0:
            return ''
        denom = max(1, bar_w - 1)
        three_stops = bar_w >= self.SPEC_MID_MIN_WIDTH
        parts = []
        for i in range(filled):
            r, g, b = self._spec_rgb_at(i / denom, idx, three_stops)
            parts.append(f'\033[38;2;{r};{g};{b}m{BarChars.HEAVY}')
        return ''.join(parts)

    def openspec_bar(self, name: str, done: int, total: int, box_width: int = 80, title_w: int = 25, idx: int = 0) -> str:
        pct = done * 100 // total
        if len(name) > title_w:
            title = name[:max(1, title_w - 3)] + '...'
        else:
            title = name.ljust(title_w)
        suffix_visible = 7 + len(str(done)) + len(str(total))
        bar_w = max(4, (box_width - 3) - (title_w + 1) - suffix_visible)
        filled = done * bar_w // total
        empty = bar_w - filled

        bar_filled = self.spec_gradient_bar(filled, bar_w, idx)
        if filled > 0 and empty > 0:
            denom = max(1, bar_w - 1)
            three_stops = bar_w >= self.SPEC_MID_MIN_WIDTH
            cr, cg, cb = self._spec_rgb_at(filled / denom, idx, three_stops)
            r, g, b = int(cr * 0.45), int(cg * 0.45), int(cb * 0.45)
            bar_filled += f'\033[38;2;{r};{g};{b}m{BarChars.HEAVY}'
            empty -= 1
        bar_empty = f'{self.spec_empty_ansi}{BarChars.HEAVY * empty}\033[0m'

        return (
            f'{CLR_WHITE_BRT}{ITALIC}{title}{RESET}{self.R} '
            f'{bar_filled}{self.R}{bar_empty}'
            f' {self.LABEL}{done}/{total}{self.R} {BOLD}{pct:>3d}%{RESET}'
        )

    def helper(self, five_hour: RateBucket) -> str:
        pct_clr = self.fill_colour(float(five_hour.used_percentage or 0))
        try:
            if not five_hour.resets_at:
                if not five_hour.used_percentage:
                    return '∞'
                return f'{pct_clr}{five_hour.used_percentage}%{self.R} {self.COMMIT}∞'
            resets_at = datetime.fromtimestamp(five_hour.resets_at).astimezone()
            delta = resets_at - datetime.now().astimezone().replace(microsecond=0)
            if delta.total_seconds() <= 0:
                if not five_hour.used_percentage:
                    return '∞'
                return f'{pct_clr}{five_hour.used_percentage}%{self.R} {self.COMMIT}∞'
            return f'{pct_clr}{five_hour.used_percentage}%{self.R} {self.COMMIT}T-{delta}'
        except Exception as e:
            return f'{e.__class__.__name__}, {str(e)}'

@dataclass
class RowSpec:
    kind: str  # 'top_border', 'bottom_border', 'separator', 'separator_dim', 'content'
    content: str = ''
    ups: tuple[int, ...] = ()
    downs: tuple[int, ...] = ()


@dataclass
class LayoutSpec:
    width: int
    fill: float
    session_id: str
    rows: list[RowSpec] = field(default_factory=list)


def _session_label(session_id: str, transcript_path: str = '', name: str = '') -> str:
    """Top-border label: `{name} | {session_id}` when a /rename name or AI-title is set, else just the id.

    `name` comes straight from the harness (`session_name`); the on-disk lookup
    is only a fallback for versions that don't send it.
    """
    if not name:
        name = SessionName.lookup(session_id, transcript_path).name
    sid = short_session_id(session_id)
    if not name:
        return sid
    return f'{GLYPH_SESSION_NAME} {name} | {sid}'


def build_narrow(session: SessionInfo, width: int, r: Renderer) -> LayoutSpec:
    ctx          = session.context_window
    fill         = 1.0

    effort_for_bg = session.effort.level if session.thinking.enabled else ''

    max_right    = max(8, width // 2)
    rate_text, right_text, right_w = r.model_right_section_compact(
        session.model_name, session.rate_limits, max_right, effort_for_bg,
    )
    line_context = r.context_line_compact(ctx, width - 3)

    subagents = RunningSubagents.from_session(session.session_id, session.workspace.project_dir)
    spec = LayoutSpec(width=width, fill=fill, session_id=_session_label(session.session_id, session.transcript_path, session.session_name))
    rate_w = _visible_width(rate_text)
    pad    = max(1, (width - 4) - rate_w - right_w)
    full   = f'{rate_text}{" " * pad}{right_text}'
    rows: list[RowSpec] = [
        RowSpec('top_border'),
        RowSpec('content', content=full),
        RowSpec('separator_dim'),
    ]
    if subagents.subagents:
        rows.append(RowSpec('content', content=r.subagent_header(len(subagents.subagents))))
        for sub in subagents.subagents:
            for line in r.subagent_row(sub, width).split('\n'):
                rows.append(RowSpec('content', content=line))
        rows.append(RowSpec('separator_dim'))
    rows.append(RowSpec('content', content=line_context))
    rows.append(RowSpec('bottom_border'))
    spec.rows = rows
    return spec


def build_medium(session: SessionInfo, width: int, r: Renderer) -> LayoutSpec:
    ctx          = session.context_window
    fill         = 1.0

    effort_for_bg = session.effort.level if session.thinking.enabled else ''

    git          = GitInfo.from_cwd(session.cwd, session.workspace.git_worktree, session.workspace.repo.url)
    line_context = r.context_line_compact(ctx, width - 3)

    max_right    = max(8, width // 2)
    rate_text, right_text, right_w = r.model_right_section_compact(
        session.model_name, session.rate_limits, max_right, effort_for_bg,
    )

    spec = LayoutSpec(width=width, fill=fill, session_id=_session_label(session.session_id, session.transcript_path, session.session_name))

    vsep_w   = 5
    rate_w   = _visible_width(rate_text)
    target_w = (width - 4) - vsep_w - rate_w - right_w
    line_path = r.fit_path(session.short_pwd, git, '', target_w, compact_only=True)
    path_w   = _visible_width(line_path)

    path_div_col = 3 + path_w + 2
    vsep = r.vsep_block(path_div_col, width, fill=fill, leader=True)
    content = f'{line_path}{vsep}{rate_text}'
    pad  = max(1, (width - 3) - (path_w + vsep_w + rate_w + right_w))
    full = f'{content}{" " * pad}{right_text}'
    top_row     = RowSpec('top_border', downs=(path_div_col,))
    content_row = RowSpec('content', content=full)
    sep_row     = RowSpec('separator_dim', ups=(path_div_col,))
    tasks     = TaskList.from_session(session.transcript_path)
    subagents = RunningSubagents.from_session(session.session_id, session.workspace.project_dir)
    rows: list[RowSpec] = [top_row, content_row, sep_row]
    if tasks.is_visible():
        rows.append(RowSpec('content', content=r.task_row(tasks, width, compact=True)))
        rows.append(RowSpec('separator_dim'))
    if subagents.subagents:
        rows.append(RowSpec('content', content=r.subagent_header(len(subagents.subagents))))
        for sub in subagents.subagents:
            for line in r.subagent_row(sub, width).split('\n'):
                rows.append(RowSpec('content', content=line))
        rows.append(RowSpec('separator_dim'))
    rows.append(RowSpec('content', content=line_context))
    rows.append(RowSpec('bottom_border'))
    spec.rows = rows
    return spec


def build_wide(session: SessionInfo, width: int, r: Renderer) -> LayoutSpec:
    ctx          = session.context_window
    fill         = 1.0

    effort_for_bg = session.effort.level if session.thinking.enabled else ''

    skills        = LoadedSkills.from_transcript(session.transcript_path)
    skill_display = ','.join(s.split(':', 1)[-1] for s in skills.names)
    subagents     = RunningSubagents.from_session(session.session_id, session.workspace.project_dir)
    tasks         = TaskList.from_session(session.transcript_path)
    elapsed       = fmt_duration_ms(session.cost.total_duration_ms)
    activity      = ActivityState.from_session(session.session_id)
    monitors      = RunningMonitors.from_session(session.session_id).monitors

    git          = GitInfo.from_cwd(session.cwd, session.workspace.git_worktree, session.workspace.repo.url)
    helper_text, right_text, right_w = r.model_right_section(
        session.model_name, session.model_thinking, session.rate_limits,
        session.effort.level if session.thinking.enabled else '',
        fast_mode=session.fast_mode,
        monitors=monitors,
        activity=activity,
        agent_name=session.agent.name,
    )
    plugin_names_raw = session.workspace.plugins
    line_context_probe = r.context_line(ctx, width - 3, session.cost)
    ctx_w_probe = _visible_width(line_context_probe)
    plugins_budget = max(0, (width - 4) - ctx_w_probe - 5)  # 5 = vsep block width
    plugins_line = r.plugins_skills(len(skills.names), skill_display, plugin_names_raw, plugins_budget)
    changes      = OpenSpec.from_cwd(session.cwd).changes
    title_cap    = max(10, width - 45)
    title_w      = min(40, title_cap, max((len(n) for n, _, _ in changes), default=25))
    openspec_bars = [r.openspec_bar(name, d, t, width, title_w, i) for i, (name, d, t) in enumerate(changes)]

    line_context = r.context_line(ctx, width - 3, session.cost)

    # The cwd rides in the top border after the session id, so row 1 opens on
    # the ref and keeps its width for the git detail.
    label_name = session.session_name or SessionName.lookup(session.session_id, session.transcript_path).name
    spec = LayoutSpec(width=width, fill=fill,
                      session_id=r.border_label(session.session_id, label_name,
                                                session.short_pwd, git, width - 4))
    rows: list[RowSpec] = []

    vsep_w   = 5
    helper_w = _visible_width(helper_text)
    weekly_text = r.weekly_segment(session.rate_limits.seven_day)
    weekly_w    = _visible_width(weekly_text)
    n_vseps  = 3 if weekly_text else 2
    target_w = (width - 4) - vsep_w * n_vseps - helper_w - weekly_w - right_w
    line_path = r.fit_path(session.short_pwd, git, elapsed, target_w, session.pr,
                           compact_only=False, show_path=False)
    path_w   = _visible_width(line_path)

    path_div_col  = 3 + path_w + 2
    model_start   = path_div_col + 3
    model_end     = model_start + right_w - 1
    model_div_col = model_end + 2
    # Weekly usage sits in its own column between the model section and the
    # activity/monitors helper, so it gets a divider of its own.
    weekly_div_col = model_div_col + weekly_w + 4

    vsep1 = r.vsep_block(path_div_col,  width, fill=fill, leader=True)
    vsep2 = r.vsep_block(model_div_col, width, fill=fill, leader=True)
    if weekly_text:
        vsep3   = r.vsep_block(weekly_div_col, width, fill=fill, leader=True)
        content = f'{line_path}{vsep1}{right_text}{vsep2}{weekly_text}{vsep3}{helper_text}'
        downs   = (path_div_col, model_div_col, weekly_div_col)
    else:
        content = f'{line_path}{vsep1}{right_text}{vsep2}{helper_text}'
        downs   = (path_div_col, model_div_col)
    rows += [
        RowSpec('top_border', downs=downs),
        RowSpec('content', content=content),
    ]

    # Combine context + plugins/skills on one row separated by a vsep.
    ctx_w = _visible_width(line_context)
    if plugins_line:
        ctx_div_col = 3 + ctx_w + 2
        ctx_vsep    = r.vsep_block(ctx_div_col, width, fill=fill, leader=True)
        combined    = f'{line_context}{ctx_vsep}{plugins_line}'
        rows.append(RowSpec('separator_dim', ups=downs, downs=(ctx_div_col,)))
        rows.append(RowSpec('content', content=combined))
        ctx_ups: tuple[int, ...] = (ctx_div_col,)
    else:
        rows.append(RowSpec('separator_dim', ups=downs))
        rows.append(RowSpec('content', content=line_context))
        ctx_ups = ()

    # First separator below the static path/context/plugins block is drawn as the
    # heavy "seam" marking the static→dynamic split. Only the first one — later
    # inter-section separators keep their normal style. When nothing dynamic
    # follows, no seam is drawn (the bottom border closes off).
    pending_ups: tuple[int, ...] = ctx_ups
    seam_pending = True

    def sep_kind(normal: str) -> str:
        nonlocal seam_pending
        if seam_pending:
            seam_pending = False
            return 'separator_seam'
        return normal

    if tasks.is_visible():
        rows.append(RowSpec(sep_kind('separator_dim'), ups=pending_ups))
        rows.append(RowSpec('content', content=r.task_row(tasks, width)))
        pending_ups = ()

    if subagents.subagents:
        rows.append(RowSpec(sep_kind('separator_dim'), ups=pending_ups))
        rows.append(RowSpec('content', content=r.subagent_header(len(subagents.subagents))))
        for sub in subagents.subagents:
            for line in r.subagent_row(sub, width).split('\n'):
                rows.append(RowSpec('content', content=line))
        pending_ups = ()

    if openspec_bars:
        rows.append(RowSpec(sep_kind('separator'), ups=pending_ups))
        for bar in openspec_bars:
            rows.append(RowSpec('content', content=bar))
        rows.append(RowSpec('bottom_border'))
    else:
        rows.append(RowSpec('bottom_border', ups=pending_ups))

    spec.rows = rows
    return spec


def render_layout(spec: LayoutSpec, r: Renderer) -> list[str]:
    lines: list[str] = []
    for row in spec.rows:
        if row.kind == 'top_border':
            lines.append(r.border_top(spec.width, spec.session_id, downs=row.downs, fill=spec.fill))
        elif row.kind == 'bottom_border':
            lines.append(r.border_bottom(spec.width, ups=row.ups, fill=spec.fill))
        elif row.kind == 'separator':
            lines.append(r.border_separator(spec.width, ups=row.ups, fill=spec.fill))
        elif row.kind == 'separator_seam':
            # Static→dynamic split: a full-brightness solid rule (vs the dotted-dim
            # separators between dynamic sections). Renders via the solid separator.
            lines.append(r.border_separator(spec.width, ups=row.ups, fill=spec.fill))
        elif row.kind == 'separator_dim':
            lines.append(r.border_separator_dim(spec.width, downs=row.downs, ups=row.ups, fill=spec.fill))
        elif row.kind == 'content':
            lines.append(r.border_line(row.content, spec.width, fill=spec.fill))
    return lines


def resolve_theme(cli_name: str | None) -> Theme:
    """Layered theme selection: CLI → env → config file → CLAUDE_DARK."""
    if cli_name and cli_name in THEMES:
        return THEMES[cli_name]
    env = os.environ.get('CLAUDE_STATUSLINE_THEME', '').strip()
    if env in THEMES:
        return THEMES[env]
    try:
        cfg = (CLAUDE_DIR / 'statusline-theme').read_text().strip()
        if cfg in THEMES:
            return THEMES[cfg]
    except OSError:
        pass
    return CLAUDE_DARK


def render(session_info: dict, width: int, *, theme: Theme | None = None) -> str:
    if width < MIN_WIDTH:
        return ''
    session = SessionInfo.from_dict(session_info)
    r       = Renderer(theme=theme)
    if width < NARROW_WIDTH:
        spec = build_narrow(session, width, r)
    elif width < MEDIUM_WIDTH:
        spec = build_medium(session, width, r)
    else:
        spec = build_wide(session, width, r)
    return '\n'.join(render_layout(spec, r))


def main() -> None:
    # Force UTF-8 on stdout so the script renders correctly on Windows
    # (cp1252 default codec can't encode box-drawing or Nerd Font glyphs,
    # crashes with UnicodeEncodeError on the first border char). Python's
    # PEP 540 UTF-8 mode and PYTHONIOENCODING env var both fix this from
    # the outside; reconfiguring stdout here removes the requirement that
    # callers set either. No-op on platforms whose default codec is
    # already UTF-8 (most Unix systems since Python 3.7).
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    theme_name: str | None = None
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == '--theme' and args:
            theme_name = args.pop(0)
        elif a.startswith('--theme='):
            theme_name = a.split('=', 1)[1]

    info  = json.loads(sys.stdin.read())
    theme = resolve_theme(theme_name)

    # Write payload so the multi-session observer can index it.
    try:
        out_dir = CLAUDE_DIR / 'statusline-output'
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f'statusline.{int(time.time())}.json').write_text(json.dumps(info))
    except OSError:
        pass

    raw_tw = terminal_width()
    if raw_tw < MIN_WIDTH:
        return
    width = max(MIN_WIDTH, min(MAX_WIDTH, raw_tw - 6))

    sys.stdout.write(render(info, width, theme=theme))


if __name__ == '__main__':
    main()
