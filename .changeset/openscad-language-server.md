---
"sk-skills": minor
---

Wire the [openscad-LSP](https://github.com/Leathong/openscad-LSP) language server into Claude Code over `.scad` files, via a new `.lsp.json` at the plugin root, and add an `openscad-lsp` skill documenting what it can and cannot answer.

Cross-file go-to-definition through `include` and `use` chains is the capability worth having: the server reads those targets from disk itself, so a definition resolves into a file nobody opened. The skill exists because three things a reader would reasonably assume are absent. Find references is not implemented and the server never replies to the request at all; rename only ever rewrites the current file and refuses when the definition lives elsewhere; diagnostics are tree-sitter parse errors rather than anything semantic.

The language server binary is installed separately with `cargo install openscad-lsp`.
