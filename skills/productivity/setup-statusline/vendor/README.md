# Vendored statusline renderer

This directory is a point-in-time snapshot of [tmck-code/yet-another-statusline](https://github.com/tmck-code/yet-another-statusline) (YAS), taken with local customizations already applied. It is licensed BSD 3-Clause; see [LICENSE](./LICENSE), which retains the upstream copyright notice.

The snapshot was taken from a working tree that sat 479 commits behind upstream `main`, with the customizations uncommitted. It is not a fork tracking upstream, and a `git pull` will not update it. Treat this directory as the source of truth: edit the status line here, and re-run the installer to push the change out to each harness.

| File | Role |
| --- | --- |
| `statusline_command.py` | The renderer. Reads a session payload as JSON on stdin, writes ANSI to stdout. Exposes `render(info, width, theme=...)`, which is the seam the Copilot adapter calls. |
| `statusline/themes.py` | Theme and colour definitions. Loaded by `statusline_command.py` via `importlib` from a path relative to itself, so the two must stay side by side. |
| `resume-handler/` | macOS handler backing the clickable session id in the status line border. Registers a `claude-resume://` URL scheme that copies `claude --resume <uuid>` to the clipboard. Optional, and macOS only. |

Rendering the glyphs needs a [Nerd Font](https://www.nerdfonts.com/font-downloads).
