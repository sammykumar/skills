## What it does

Tells you what the OpenSCAD language server can and cannot answer, so an agent editing `.scad` never presents a guess as a resolved symbol. The `sk-skills` plugin wires [openscad-LSP](https://github.com/Leathong/openscad-LSP) into Claude Code over `.scad` files, and this skill is the page that travels with it.

It is not a driver. Nothing in it invokes the server; Claude Code does that. The skill exists because the server is far narrower than its own README implies, and the interesting content is the **boundary**: three capabilities a reasonable reader would assume are present and are not.

## When to reach for it

- **Invocation mode.** Model-invoked. Type `/openscad-lsp`, or the agent reaches for it automatically when OpenSCAD source is in play.
- **Trigger boundary.** Reach for this when a module or variable will not resolve, when following an `include` or `use` chain, or when a rename or a symbol search is being planned across `.scad` files.

## Prerequisites

The language server is a separate binary. Plugins configure a language server, they do not bundle one.

```bash
cargo install openscad-lsp
```

Without it, `.scad` files get no intelligence at all, and the `/plugin` Errors tab reports that the executable was not found in `$PATH`.

## The boundary

The three absences are the whole point of the page.

| Assumption | Reality |
| --- | --- |
| Find references works | It does not exist. The server never replies to the request, so a client that asks hangs rather than erroring. Grep the `include` and `use` graph instead. |
| Rename is safe across files | It rewrites the current file only, and refuses outright when the definition lives elsewhere. Consumers in other files are untouched. |
| Diagnostics catch mistakes | They are tree-sitter parse errors. An undefined variable, a module called with wrong arguments, or geometry that fails to render all pass silently. |

What genuinely works, and is the reason to have it at all, is **cross-file go-to-definition**. The server reads `include` and `use` targets from disk itself, so a definition resolves into a file nobody opened. That is the query grep cannot cheaply give you.

## Common questions

**Why do no diagnostics appear when I just open a `.scad` file?**
The server only publishes diagnostics after an edit, never on open. Nothing is wrong; there is simply no analysis until the document changes. In practice this is invisible, because Claude Code edits files, and an edit is exactly what triggers them.

**Why does find references hang rather than return nothing?**
The server does not implement the request and never sends a reply, so anything waiting on one waits forever. That is why the skill tells you to grep the `include` and `use` graph instead of asking.

**Nothing resolves at all. What is wrong?**
Almost always the binary is missing, because the plugin configures a language server but does not ship one. Check the `/plugin` Errors tab for a missing executable, and install it with `cargo install openscad-lsp`.

## It's working if

- Go-to-definition on a module called in one file lands in the file that `include`s or `use`s it, without that file being open.
- Hovering a module shows its signature and the comment written above it.
- A broken edit to a `.scad` file surfaces a `syntax error` with a line range shortly after the edit.
- When something does not resolve, the answer names which cause it is (server missing, path outside every library location, builtin) rather than guessing at the symbol.

## Where it fits

A **reach-for-it-anytime standalone**, and the only skill here whose subject is a piece of plugin configuration rather than a process. It sits underneath any flow that touches OpenSCAD: `/diagnosing-bugs` on a model that will not render, or `/implement` on a parametric part. Its nearest neighbour is [research](../engineering/research.md), because the honest thing to do when the server cannot answer is go read the source rather than assert. For the map over the whole set, see [ask-sk](../engineering/ask-sk.md).
