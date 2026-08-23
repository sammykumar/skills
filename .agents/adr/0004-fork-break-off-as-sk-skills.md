# Break this fork off as `sk-skills`, shipped from its own single-plugin marketplace

This repo began as a fork of [mattpocock/skills](https://github.com/mattpocock/skills), dogfooded locally. We now ship it as an independently branded plugin, `sk-skills`, installed from this repo's own marketplace, so it can be installed the same plug-and-play way in other SK Productions repos.

## Decision

- The plugin is **`sk-skills`**; the marketplace alias is **`sammykumar`**, backed by `.claude-plugin/marketplace.json` in this repo (`sammykumar/skills`).
- Install route: `/plugin marketplace add sammykumar/skills` then `/plugin install sk-skills@sammykumar`. The wording lives in [.agents/install-block.md](../install-block.md).
- This fork is **not** in any Anthropic-official marketplace. ADR 0002's "Update, 2026-08-05" (official-marketplace listing, auto-update) describes **upstream** `mattpocock-skills` only and does not apply here. The self-marketplace route ADR 0002 called a fallback is, for this fork, the primary and only route.
- Version reset to **1.0.0** as the fork's first line; `package.json` and `.claude-plugin/plugin.json` stay in sync via `scripts/sync-plugin-version.mjs` as before.
- Matt Pocock's MIT copyright is retained in `LICENSE` (MIT requires it); a second copyright line for Sam Kumar is added.

## Rename mapping (upstream name → fork name)

Two skills carried the upstream author's name and were renamed:

- `ask-matt` → `ask-sk`
- `setup-matt-pocock-skills` → `setup-sk-skills`

Each rename touched the skill directory, `SKILL.md` `name:` frontmatter and heading, the paired `agents/openai.yaml` `display_name`, the `plugin.json` skills path, the mirrored `docs/engineering/<name>.md`, and every inbound reference.

## Staying a fork

We keep an `upstream` remote (`https://github.com/mattpocock/skills.git`) to merge Matt's future skills. Full rebrand plus staying a fork means upstream merges will conflict on the two renamed skills and on stripped author names. This rename mapping is the record that makes those merges resolvable: when upstream touches `ask-matt` or `setup-matt-pocock-skills`, apply the change to the renamed path here.

## Docs and site

`docs/` pages no longer publish to `aihero.dev` (that is upstream's site). They are kept as in-repo docs, command-free, with the `aihero.dev/skills-<name>` URL claims removed. `.agents/writing-docs.md` is updated to match.
