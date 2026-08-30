# Ship language servers as plugin config, not as a bundled LSP client

The plan for OpenSCAD support was a skill plus a dependency-free Node CLI that spoke LSP over stdio to [openscad-LSP](https://github.com/Leathong/openscad-LSP), exposing `definition`, `hover`, `symbols` and friends as subcommands, with hand-rolled `Content-Length` framing and a test suite over it. That plan predated knowing that Claude Code plugins can declare language servers natively.

We ship [.lsp.json](../../.lsp.json) instead. Claude Code launches `openscad-lsp --stdio` itself and consumes definition, hover, symbols and diagnostics directly, so the client, its framing code, and its tests are all work we do not do and do not maintain.

## Considered options

- **Bundled `.mjs` client.** Rejected. It reimplements by hand what the harness already does, and every line of JSON-RPC framing is a line that can go wrong in a way no OpenSCAD user would be able to debug.
- **Both, native config plus a thin client for explicit queries.** Rejected for now. The marginal cases the client would cover (an explicitly invoked `format`, Codex parity) do not justify maintaining a hand-rolled LSP client forever. Revisit if the native path proves insufficient in practice.
- **`lspServers` inline in `.claude-plugin/plugin.json`.** Rejected in favour of a real `.lsp.json` at the plugin root. Both are documented, but there is a live class of bugs where LSP config declared in a manifest does not survive plugin installation, leaving the installed plugin with no LSP config at all ([claude-code#16219](https://github.com/anthropics/claude-code/issues/16219), [claude-plugins-official#379](https://github.com/anthropics/claude-plugins-official/issues/379)). A file in the source tree survives every install path.

## Consequences

- **The plugin now ships something that is not a skill.** `.lsp.json` sits beside `.claude-plugin/`, and `CLAUDE.md` records it so the next author does not read it as a stray file.
- **Language servers are Claude Code only.** There is no Codex equivalent, so `openscad-lsp`'s `SKILL.md` states that boundary in its own body rather than promising navigation Codex cannot perform. This deepens the asymmetry [0002](./0002-ship-as-a-claude-code-plugin.md) already accepted.
- **The binary is still the user's to install.** Plugins configure a language server, they do not bundle one. `cargo install openscad-lsp` is a prerequisite, and the skill leads with it as the first thing to check when nothing resolves.
- **Optional fields are left unset on purpose.** Before Claude Code v2.1.205, setting `restartOnCrash` or `shutdownTimeout` caused the server to be skipped entirely, with the reason visible only under `claude --debug`. Defaults avoid that failure mode.
