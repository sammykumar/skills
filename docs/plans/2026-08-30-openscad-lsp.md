# OpenSCAD language server support in `sk-skills`

The ask was a skill giving an agent real language-server intelligence over OpenSCAD source, backed by [openscad-LSP](https://github.com/Leathong/openscad-LSP), planned as a `SKILL.md` plus a bundled dependency-free Node CLI speaking LSP over stdio. Research reshaped it twice: the server does far less than its README implies, and Claude Code can host a language server natively, which removes the reason to write a client at all.

## Research findings

Read off openscad-LSP v2.0.3's source and then confirmed by driving the installed binary over stdio against a two-file fixture.

The complete handled request set is hover, completion, definition, documentSymbol, formatting, prepareRename, rename. That is it.

| Claim in the original plan | What the server actually does |
| --- | --- |
| `references` | **Absent.** No `referencesProvider`, and the request gets no response at all: the server logs `unknown request` and never replies, so a waiting client hangs rather than erroring. |
| Safe cross-file `rename` | **Single file only.** It errors with "renaming symbols defined in another file is not yet supported", and the `WorkspaceEdit` it returns always carries exactly one URI. Scope-aware within the file, which still beats `sed`. |
| `diagnostics` | Present, but pushed **only on `didChange`**, never on `didOpen`, and they are tree-sitter parse errors, not OpenSCAD semantic errors, and the one include-resolution diagnostic among them only fires on a single-range edit landing on the include statement. A client that opens a file and waits for diagnostics waits forever. |

Two findings in the other direction. The server reads `include` and `use` targets **from disk itself**, so cross-file go-to-definition works with only the entry file opened. And all its logging goes through `eprintln!` to stderr, leaving stdout protocol-only, which is Claude Code's hard requirement for a hosted language server.

Verified live: definition from `main.scad` resolved through `include <lib.scad>` into `lib.scad`; hover returned the signature plus the doc comment; `documentSymbol` returned the module on the file that defines it and `[]` on the file that only calls it; formatting reflowed via topiary; a `didChange` introducing a broken module produced a `syntax error` diagnostic; `references` produced nothing.

## Resolved design

### Mechanism: native plugin LSP config, no client

`.lsp.json` at the plugin root declaring `openscad-lsp --stdio` for `.scad`. Claude Code launches and drives the server; we write no LSP code.

_Why:_ the bundled-client plan predated knowing this surface existed. It reimplements by hand what the harness already does. The trade-offs, the rejected alternatives, and why `.lsp.json` beat inline `lspServers`, are in [ADR 0008](../../.agents/adr/0008-ship-language-servers-not-a-bundled-lsp-client.md).

### Config: minimal, defaults everywhere

`command`, `args`, `extensionToLanguage` only. Diagnostics injection is left on at its default, because tree-sitter parse errors are exactly the class of mistake an agent makes hand-editing `.scad`, and they fire on `didChange`, which is precisely when Claude Code edits.

`restartOnCrash` and `shutdownTimeout` are deliberately unset: before Claude Code v2.1.205 setting either caused the server to be skipped entirely, visible only under `claude --debug`.

Library paths are left to the server. It already reads `OPENSCADPATH` at startup and falls back to the per-user and installation OpenSCAD library directories. A hardcoded `search_paths` in a shipped manifest would bake one machine's paths into everyone's config.

### The skill: a capability boundary, not a driver

`skills/engineering/openscad-lsp/`, model-invoked, triggering on OpenSCAD source rather than on failure symptoms. By the time navigation visibly fails, the model has already trusted a capability that is not there.

Its content is the three absences above, plus the resolution ladder for a symbol that will not resolve: server not installed (`cargo install openscad-lsp`), dependency outside every library path, or a builtin. Builtins are worth their own rung, because they are the one case where hover works and go-to-definition returns empty: verified by probe, `cube` and `sin` both hover with full documentation and return `[]` for definition.

_Why a skill at all,_ when this is plugin config: without it nothing tells the model in-context where the intelligence stops, and the failure mode is a confident wrong answer about a symbol the server never resolved.

### Dual harness

`agents/openai.yaml` ships as the repo requires, and the `SKILL.md` body states that the wiring is Claude Code's and that Codex has no equivalent. The alternative, staying silent, reads to a Codex agent as a promise of navigation it cannot perform.

## What was deliberately not built

The `.mjs` LSP client, its hand-rolled `Content-Length` framing, its `.scad` fixtures, and its test suite. The whole reason the original plan needed them is handled by the harness.

## Tasks

- [x] `.lsp.json` at the repo root
- [x] `skills/engineering/openscad-lsp/SKILL.md` and `agents/openai.yaml`
- [x] ADR 0008
- [x] `CLAUDE.md` section recording that the plugin ships language servers as well as skills
- [x] `docs/engineering/openscad-lsp.md`
- [x] `plugin.json` skills array, top-level `README.md`, `skills/engineering/README.md`, `ask-sk`
- [x] Changeset
- [x] Dogfood against the `3d-printing` repo's cross-file `include` chain
- [ ] After release, confirm Claude Code actually discovers `.lsp.json` and attaches the server (see below)

## Dogfood

Run against `3d-models/igla-fob-housing-replacement/tools-review/gates.scad` in the `3d-printing` repo, which reaches its dependencies through `include <../igla-fob-housing.scad>`, a parent-directory hop.

With only `gates.scad` opened, definition resolved `pcb2d` and `back_half` into `igla-fob-housing.scad`, and resolved the top-level variable `seat_z` there as well, so variables cross files the same way modules do. Hover returned each one's signature along with the doc comment written above it in the other file.

### Still unverified: the hosting hop

The dogfood above drove `openscad-lsp` directly over stdio. It did not exercise Claude Code's hosting of it, because `.lsp.json` only takes effect through an installed plugin, and the installed `sk-skills` is still 2.2.0.

That the plugin root is the repo root, and that Claude Code discovers `.lsp.json` there and attaches the server, is read from the plugins reference rather than observed. It is also precisely the hop where the install-propagation bugs cited in ADR 0008 live, which is why the config is a real file rather than a manifest field.

Half of it is now settled. The installed plugin cache keeps the whole repo tree per version, dotfiles included: `~/.claude/plugins/cache/sammykumar/sk-skills/2.2.0/` holds `.agents`, `.changeset`, `.claude-plugin`, `.github` and `.gitignore`. A root-level `.lsp.json` will therefore arrive at the plugin root on install, which is the specific thing the bugs behind ADR 0008 break for manifest-declared config.

What is left is whether Claude Code reads it there and attaches the server. Confirm after the next release reaches this machine: open a `.scad` file in the `3d-printing` repo, check the `/plugin` Errors tab reports no missing executable, and check `claude --debug` does not report the server as skipped.
