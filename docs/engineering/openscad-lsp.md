## What it does

Tells you what the OpenSCAD language server can and cannot answer, so an agent editing `.scad` never presents a guess as a resolved symbol. The `sk-skills` plugin wires [openscad-LSP](https://github.com/Leathong/openscad-LSP) into Claude Code over `.scad` files, and this skill is the page that travels with it.

It is not a driver. Nothing in it invokes the server; Claude Code does that. The skill exists because the server is far narrower than its own README implies, and the interesting content is the **boundary**: three capabilities a reasonable reader would assume are present and are not.

## When to reach for it

- **Invocation mode.** Model-invoked. Type `/openscad-lsp`, or the agent reaches for it automatically when OpenSCAD source is in play.
- **Trigger boundary.** Reach for this when a module or variable will not resolve, when following an `include` or `use` chain, or when a rename or a symbol search is being planned across `.scad` files.

## Prerequisites

The `openscad-lsp` binary, installed separately through cargo. Plugins configure a language server, they do not bundle one, so without it `.scad` files get no intelligence at all and Claude Code reports a missing executable rather than starting anything. The skill itself carries the command.

## The boundary

The three absences: **find references**, which is unimplemented and never even replies; **cross-file rename**, which is refused outright; and **semantic diagnostics**, which never arrive, because what does arrive is tree-sitter parse errors. The skill spells out what each one does instead, and what to do about it.

What genuinely works, and is the reason to have it at all, is **cross-file go-to-definition**. The server reads `include` and `use` targets from disk itself, so a definition resolves into a file nobody opened. That is the query grep cannot cheaply give you.

## Common questions

**Why do no diagnostics appear when I just open a `.scad` file?**
The server only publishes diagnostics after an edit, never on open. Nothing is wrong; there is simply no analysis until the document changes, and an edit is what triggers them.

**Why does find references hang rather than return nothing?**
The server does not implement the request and never sends a reply, so anything waiting on one waits forever. That is why the skill tells you to grep the `include` and `use` graph instead of asking.

## It's working if

- Go-to-definition on a module called in one file lands in the file that `include`s or `use`s it, without that file being open.
- Hovering a module shows its signature and the comment written above it.
- A broken edit to a `.scad` file surfaces a `syntax error` with a line range shortly after the edit.
- When something does not resolve, the answer names which cause it is (server missing, path outside every library location, builtin) rather than guessing at the symbol.

## Where it fits

A **reach-for-it-anytime standalone**, and the only skill here whose subject is a piece of plugin configuration rather than a process. It sits underneath any flow that touches OpenSCAD: `/diagnosing-bugs` on a model that will not render, or `/implement` on a parametric part. Its nearest neighbour is [research](../engineering/research.md), because the honest thing to do when the server cannot answer is go read the source rather than assert. For the map over the whole set, see [ask-sk](../engineering/ask-sk.md).
