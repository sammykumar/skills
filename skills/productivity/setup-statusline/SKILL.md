---
name: setup-statusline
description: "Install the custom terminal status line across your coding agents: the full renderer for Claude Code and GitHub Copilot CLI, and the closest built-in approximation for Codex. Run once per machine, or again after changing the renderer."
disable-model-invocation: true
---

# Setup Statusline

Installs one status line across three harnesses. Claude Code and Copilot CLI run the real renderer; Codex gets an approximation built from its own built-in items, because it cannot run a command for its status line at all.

Ask which harnesses to set up, then run only those steps. Each script is idempotent and backs up the settings file it edits, so re-running is safe.

## What each harness can actually do

| Harness | Mechanism | Result |
| --- | --- | --- |
| Claude Code | `statusLine.command` in `settings.json`: JSON on stdin, ANSI on stdout | The real renderer |
| Copilot CLI | `statusLine.command` in `settings.json`: same contract, different payload shape | The real renderer, through an adapter |
| Codex | `tui.status_line`: a fixed enum of built-in items | An approximation only |

Codex's `tui.status_line` accepts only built-in item names. There is no hook for rendering the output of an external command, so the renderer cannot run there. Do not tell the user otherwise, and do not attempt a workaround: the request for command-backed rendering ([openai/codex#20140](https://github.com/openai/codex/issues/20140)) was closed as a duplicate and remains unimplemented.

## Prerequisites

- `python3` on `PATH`. The renderer is Python and has no third-party dependencies.
- A [Nerd Font](https://www.nerdfonts.com/font-downloads) selected in the terminal. Without one the glyphs render as tofu boxes, which is the single most common "it looks broken" report.

## Steps

### 1. Claude Code

```bash
skills/productivity/setup-statusline/scripts/install-claude.sh
```

Symlinks `vendor/statusline_command.py` and `vendor/statusline/themes.py` into the Claude config dir and points `settings.json` at the first. They are symlinks, not copies, so editing the skill changes the live status line with no reinstall.

If the user already ran the upstream project's own `make install`, those same two paths are symlinks into that clone. This script repoints them at the skill. Say so when it happens, because it means the skill becomes the one source of truth and edits to the old clone stop having any effect.

### 2. Copilot CLI

```bash
skills/productivity/setup-statusline/scripts/install-copilot.sh
```

Points `~/.copilot/settings.json` at `scripts/copilot-statusline.py`, which translates Copilot's payload into the shape the renderer expects and then calls the same renderer. `footer.showCustom` gates the custom line; it defaults to on, and the script sets it anyway in case the `/statusline` picker turned it off.

Requires a `~/.copilot` directory, so the user must have run `copilot` at least once.

### 3. Codex

```bash
skills/productivity/setup-statusline/scripts/configure-codex.sh
```

Writes `tui.status_line` and `tui.status_line_use_colors` into `~/.codex/config.toml`, choosing the built-in items that line up with the renderer's sections in the same order. It replaces only those two keys, so anything else already under `[tui]` survives.

Tell the user they can reorder or trim the selection at any time with `/statusline` inside Codex.

### 4. Optional: the clickable session id (macOS, Claude Code only)

```bash
skills/productivity/setup-statusline/vendor/resume-handler/install.sh
```

Registers a `claude-resume://` URL scheme so clicking the session id in the status line border copies `claude --resume <uuid>` to the clipboard. macOS only. Skip it elsewhere, and skip it for Copilot, whose sessions resume with `copilot --resume=<id>` instead.

## Changing the status line later

`vendor/` is the source of truth. Edit it there and the change reaches Claude Code immediately through the symlinks, and Copilot immediately because the adapter loads the renderer by path.

`vendor/` is a snapshot of [tmck-code/yet-another-statusline](https://github.com/tmck-code/yet-another-statusline) with local customizations applied, taken from a tree that was already well behind upstream. It does not track upstream and `git pull` will not update it. See [vendor/README.md](./vendor/README.md).

## Known gaps under Copilot

State these plainly rather than letting the user discover them:

- **The activity indicator always reads `idle`.** It is driven by state files that Claude Code's `UserPromptSubmit` and `Stop` hooks write, and nothing writes them under Copilot.
- **No rate limit sections.** Copilot reports no 5-hour or weekly usage window, so those sections omit themselves.
- **No dollar cost.** Copilot bills in AI credits, not dollars. The adapter deliberately leaves the cost field unset rather than rendering a credit count in a currency-labelled slot.
- **The model reads `unknown` until the first turn.** Copilot sends a null model until one is resolved for the session.
