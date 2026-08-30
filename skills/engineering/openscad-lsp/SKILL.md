---
name: openscad-lsp
description: What the OpenSCAD language server can and cannot answer. Use when reading, editing, or reasoning about OpenSCAD source (.scad files), when a module or variable will not resolve, when following an include or use chain, or when a rename or a symbol search is being planned across .scad files.
---

# OpenSCAD language server

The `sk-skills` plugin wires [openscad-LSP](https://github.com/Leathong/openscad-LSP) into Claude Code over `.scad` files, in [.lsp.json](../../../.lsp.json). This skill is not a driver for it. Its job is the **capability boundary**: what the server actually answers, so you never present a guess as a resolved symbol.

The server is deliberately narrow. Assume nothing beyond the table below.

## What it answers

| Query | Behaviour |
| --- | --- |
| Go to definition | Works, **and crosses files**. The server reads `include` and `use` targets from disk itself, so a definition resolves into a file nobody opened. |
| Hover | Signature plus the doc comment written directly above the module or function. |
| Document symbols | Top-level definitions in the file. A file that only calls into an include returns an empty list, which means "nothing defined here", not "nothing found". |
| Completion | Identifiers, snippets, and `include`/`use` path completion. |
| Formatting | Whole-file reflow via topiary. |
| Diagnostics | Parse errors only, pushed after an edit. |

## What it does not answer

**Find references does not exist.** The server does not implement `textDocument/references` and does not reply to it at all, so a client that asks will wait forever rather than get an error. To find call sites, grep the `include` and `use` graph yourself.

**Rename is single file.** It rewrites the current file only, scope-aware within it, and hard-errors with "renaming symbols defined in another file is not yet supported" when the definition lives elsewhere. Even when it succeeds it has not touched consumers in other files. Treat it as a scoped rewrite, then find and update the call sites yourself.

**Diagnostics are syntax, not semantics.** They come from the tree-sitter parse: `syntax error`, `missing <node>`, and an unresolvable `include` path. An undefined variable, a module called with the wrong arguments, or geometry that fails to render will all pass silently. Only the `openscad` binary catches those, and nothing here runs it.

## When a symbol will not resolve

Work down this list before concluding the code is wrong.

1. **The server is not installed.** It is a separate binary that the plugin configures but does not ship. Fix: `cargo install openscad-lsp`.
2. **The file is outside a library path.** The server resolves `include` and `use` relative to the including file, then against `OPENSCADPATH`, then the per-user OpenSCAD libraries directory, then the OpenSCAD installation's own libraries. A dependency outside all of those is invisible to it.
3. **The definition is a builtin.** Builtins resolve for hover and definition but cannot be renamed.

Say plainly which of these applies. A confident answer from a symbol the server never resolved is worse than reporting that it could not be found.

## Under Codex

The wiring above is Claude Code's. Under Codex nothing starts the server for you, so none of these queries are available in-session, though every fact on this page still describes the tool if you reach it yourself. Fall back to reading the `include` and `use` chain directly.
