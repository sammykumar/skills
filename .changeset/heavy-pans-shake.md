---
"sk-skills": patch
---

Add `/setup-statusline`, which installs the custom terminal status line across Claude Code, GitHub Copilot CLI, and Codex.

Claude Code and Copilot CLI both spawn a command and hand it a JSON session payload on stdin, so both run the same vendored renderer; Copilot reaches it through an adapter that reshapes the payload. Codex accepts only a fixed enum of built-in items for `tui.status_line` and has no hook for command output, so it gets the closest built-in approximation instead, and the skill says so rather than implying parity.
