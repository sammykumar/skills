# The canonical install block

One install story, one wording. `README.md`, `.changeset/*`, and every page under `docs/` must say **this** and nothing else. Change it here first, then propagate.

`sk-skills` ships from this repo's own single-plugin marketplace: `.claude-plugin/marketplace.json` makes `sammykumar/skills` an installable marketplace. You add the marketplace once, then install the plugin from it. This is not in any Anthropic-official marketplace, so it must be added before it can be installed, and updates arrive when you re-run the install (or `/plugin marketplace update`), not automatically.

## Claude Code: the plugin

<canonical-block name="claude-code">

```bash
claude plugin marketplace add sammykumar/skills
claude plugin install sk-skills@sammykumar
```

Or, from inside a session:

```
/plugin marketplace add sammykumar/skills
/plugin install sk-skills@sammykumar
```

It ships from this repo's own marketplace, so add the marketplace first, then install. To pull later updates, re-run the install or `/plugin marketplace update sammykumar`.

</canonical-block>

## Codex, and other agents: skills.sh

The plugin is Claude Code only. Everywhere else, [skills.sh](https://skills.sh/sammykumar/skills) copies editable skill files into the project. Use the whole-set form on `README.md`:

<canonical-block name="skills-sh-whole-set">

```bash
npx skills@latest add sammykumar/skills
```

Pick the skills you want, and which coding agents to install them on. **The installer lets you choose which skills to take: make sure `setup-sk-skills` is one of them.**

</canonical-block>

…and the single-skill form wherever one skill is named on its own. Note that **`docs/` pages are not a consumer of this block**: a page that writes the commands out duplicates the install instructions, so keep the docs pages command-free. See [writing-docs.md](./writing-docs.md).

<canonical-block name="skills-sh-one-skill">

```bash
npx skills@latest add sammykumar/skills --skill=<name>
```

```bash
npx skills@latest update <name>
```

</canonical-block>

`skills@latest` is the pinned spelling in all three.

## The two routes are exclusive

The plugin is a managed, read-only bundle you subscribe to. skills.sh writes files you own and edit. Installing both leaves the user with every skill twice: always say "pick one".
