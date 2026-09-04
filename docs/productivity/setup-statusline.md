## What it does

Installs one custom terminal status line across every coding agent on a machine, so Claude Code, GitHub Copilot CLI, and Codex all show the same session information in the same place. One renderer, one theme, three harnesses.

The renderer is shared, not reimplemented per harness. Claude Code and Copilot CLI expose the same contract, a command that receives a JSON session payload on stdin and prints ANSI to stdout, so Copilot reaches the identical renderer through a thin adapter that only reshapes the payload. Codex is the exception that shapes the whole skill: it has no way to run a command for its status line, only a fixed list of built-in items, so it gets a deliberate approximation rather than a port.

## When to reach for it

You invoke this by typing `/setup-statusline`, and the agent won't reach for it on its own. It writes to global config outside any repo, so it stays behind a name you type.

Reach for it when:

| Situation | What you get |
| --- | --- |
| New machine, or a harness you just installed | The status line set up wherever it can run |
| You changed the renderer and want it live | Nothing to re-run for Claude Code or Copilot; the install is by reference |
| Your status line shows boxes instead of glyphs | The font prerequisite, which is nearly always the cause |
| You want the same line in Copilot as in Claude Code | The adapter, which is the only supported route |

## Prerequisites

- `python3` on `PATH`. The renderer is Python with no third-party dependencies.
- A [Nerd Font](https://www.nerdfonts.com/font-downloads) selected in the terminal, for the glyphs.
- For Copilot, a `~/.copilot` directory, which means having run `copilot` at least once.

## What each harness can actually do

This is the whole shape of the skill, so it is worth knowing before you run it:

| Harness | Mechanism | Result |
| --- | --- | --- |
| Claude Code | `statusLine.command`, JSON on stdin | The real renderer |
| Copilot CLI | `statusLine.command`, same contract, different payload | The real renderer, via an adapter |
| Codex | `tui.status_line`, a fixed enum of built-ins | An approximation only |

Codex's status line takes item names, not commands. There is no hook for external output, so no amount of configuration gets the real renderer in there. What the skill writes instead is the built-in selection that lines up most closely with the renderer's own sections, in the same order.

## The vendored renderer

The renderer lives in the skill, under `vendor/`, and that copy is the source of truth. Both working installs point at it by reference rather than copying from it: Claude Code through symlinks into its config dir, Copilot because the adapter loads it by path. Edit `vendor/` and both harnesses pick the change up on their next session, with no reinstall step.

That reference-not-copy property is also the trap to know about. If a separate clone of the upstream project is still around and its own installer has run, the two compete for the same two paths in the Claude config dir. The installer resolves this by repointing those paths at the skill, which means edits to the old clone silently stop mattering.

## Common questions

**Why doesn't Codex look like the others?**
Because it cannot. `tui.status_line` accepts only built-in item names, and the request for command-backed rendering was closed as a duplicate without being implemented. The skill configures the closest built-ins rather than pretending; you can reorder or trim them any time with `/statusline` inside Codex.

**My status line is a row of empty boxes.**
The terminal font isn't a Nerd Font. This is the most common report by a wide margin, and it is a font setting rather than anything about the install.

**Why does Copilot always say `idle`?**
The activity indicator reads state files that Claude Code's `UserPromptSubmit` and `Stop` hooks write. Nothing writes them under Copilot, so it reads idle regardless of what the session is doing.

**Why is there no cost figure under Copilot?**
Copilot bills in AI credits, not dollars. The adapter leaves the cost field unset on purpose rather than rendering a credit count in a slot labelled as currency.

**Can I re-run it?**
Yes. Every script is idempotent and backs up the settings file it edits before writing. The Codex step replaces only the two keys it owns, so anything else already under `[tui]` survives.

## It's working if

- A bordered, coloured line appears under the prompt in each harness you set up, with glyphs rather than boxes.
- The branch shown tracks the repo you're actually in, and changes when you switch directories.
- Editing `vendor/` changes what Claude Code and Copilot draw on the next session, with nothing reinstalled.
- Under Copilot the session id is plain text, not a link. It resumes with a different command than Claude Code's, so linking it would put the wrong thing on your clipboard.
- Codex shows a status line built from its own items, visibly not identical to the other two.

## Where it fits

A run-once setup, like [setup-sk-skills](../engineering/setup-sk-skills.md), except that it configures your machine rather than a repo, so it runs once per machine instead of once per project. Nothing depends on it and it depends on nothing; it is not part of any chain.

For the map of how the skills relate, see [ask-sk](../engineering/ask-sk.md).
