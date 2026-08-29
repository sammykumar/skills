---
name: update-sk-skills
description: "Update this machine's sk-skills to the latest version, by first detecting how they were actually installed: the Claude Code plugin, skills.sh, or a dev checkout."
disable-model-invocation: true
---

# Update SK Skills

Bring the installed sk-skills up to date.

There are three ways these skills reach a machine, and they are updated by three different commands. **Detect which one before running anything.** The harness you are in does not tell you: Claude Code can be on either route, and a machine can carry more than one at once.

| Route | Evidence on disk | Updated by |
| --- | --- | --- |
| Claude Code plugin | an `sk-skills@<marketplace>` entry in the installed-plugins file | `claude plugin update` |
| skills.sh | a lockfile entry whose source is `sammykumar/skills` | `npx skills@latest update` |
| Dev checkout | the skill directory is a symlink into a git working tree of the repo | `git pull` |

This is a read-then-act skill: gather the evidence, show the user what you found and what you are about to run, then run it.

## Process

### 1. Detect every installation

Run all four checks, even after one hits. Coexisting installs are the case that matters most, and stopping at the first match is how you miss them.

**A. Dev checkout.** Resolve the skill directories the harnesses read, and see whether any sk skill is a symlink into a git working tree:

```bash
for d in "$PWD/.claude/skills" "$PWD/.agents/skills" "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  [ -d "$d" ] || continue
  for s in "$d"/*; do
    [ -L "$s" ] && printf '%s -> %s\n' "$s" "$(readlink "$s")"
  done
done
```

A symlink pointing into a checkout whose root holds `.claude-plugin/plugin.json` with `"name": "sk-skills"` is a dev checkout, linked by that repo's `scripts/link-skills.sh`. Record the checkout path.

**B. Claude Code plugin.** Read the install record rather than guessing:

```bash
cat ~/.claude/plugins/installed_plugins.json
```

Look for a key matching `sk-skills@<marketplace>`. Each entry carries the `scope` (`user`, `project`, `local`, `managed`), the installed `version`, and the `installPath`. You need the marketplace name and the scope for the update command, so read them off the entry instead of assuming `sammykumar` and `user`. If the `claude` CLI is on `PATH`, `claude plugin list` is a second read on the same fact.

Also check whether the plugin is disabled here: an `enabledPlugins` entry set to `false` in the repo's `.claude/settings.json` or in `~/.claude/settings.json` means it is installed but not running in this repo, which is worth reporting rather than silently updating.

**C. skills.sh.** Two lockfiles, one per scope:

- Global: `$XDG_STATE_HOME/skills/.skill-lock.json` when `XDG_STATE_HOME` is set, otherwise `~/.agents/.skill-lock.json`
- Project: `skills-lock.json` at the root of the repo you are in (its skills land in `.agents/skills/`)

```bash
lock="${XDG_STATE_HOME:+$XDG_STATE_HOME/skills}"; lock="${lock:-$HOME/.agents}/.skill-lock.json"
[ -f "$lock" ] && cat "$lock"
[ -f skills-lock.json ] && cat skills-lock.json
```

Entries whose `source` is `sammykumar/skills` are ours. Collect their **names**: they are the subset the user chose at install time, and they are what you pass to the update command. Note which scope each lockfile represents, because the update command takes a scope flag.

**D. Hand-copied files.** `SKILL.md` files for these skills present in a skills directory as real directories rather than symlinks, with no lockfile entry and no plugin record. Nothing can update these automatically.

### 2. Report before you run anything

Show the user one table: route, where it lives, which skills it covers, the version you found, and the exact command you propose to run. Then act. Do not run an installer the user has not seen.

### 3. Take the awkward cases first

| What you found | What to do |
| --- | --- |
| **Plugin and skills.sh both present** | Say so and stop. The two routes are exclusive: the user now has every skill twice, once pinned to a release and once as editable files, with no way to tell which is running. Ask which one to keep, and offer to remove the other (`claude plugin uninstall sk-skills@<marketplace>` or `npx skills@latest remove -s <names>`) before updating the survivor. |
| **A dev checkout** | Do not run any installer against it. See step 4. |
| **Hand-copied files only** | Report it. There is no update path; the user can re-copy, or adopt one of the two supported routes. Point them at the repo's install instructions rather than writing the commands from memory. |
| **Nothing found at all** | Say so plainly. Something installed this skill, so the detection missed it: report the directories you checked and let the user tell you which route they are on rather than guessing. |

### 4. Update each confirmed installation

**Claude Code plugin.** Refresh the marketplace, then the plugin, substituting the marketplace and scope you read in step 1B:

```bash
claude plugin marketplace update <marketplace>
claude plugin update sk-skills@<marketplace> --scope <scope> -y
```

`-y` is required: it accepts the marketplace-declared install command, and the prompt cannot be answered when stdin is not a TTY, which is the case whenever you run this from inside a session. **The update does not take effect until the session restarts**; say so in the report rather than letting the user wonder why the old wording is still there.

**skills.sh.** Update only the sk skills, by name, in the scope whose lockfile listed them:

```bash
npx skills@latest update <name> <name> ... -g
```

Use `-p` instead of `-g` for a project-scoped install. Pass the names: a bare `npx skills@latest update` updates every skill from every source the user has installed, which is more than they asked for. If a skill was installed with `--copy` and has since been edited by hand, the update overwrites those edits, so flag any local modifications you can see before running it.

**Dev checkout.** These are symlinks into a working tree, so the update is a pull, not an install:

```bash
git -C <checkout> status --short
git -C <checkout> pull
<checkout>/scripts/link-skills.sh
```

Check the working tree first: if it is dirty or on a branch other than the default, report that and let the user decide rather than pulling under their work. Re-run `link-skills.sh` afterwards so skills added, renamed, or moved between buckets since the last pull are linked and stale symlinks are pruned.

### 5. Report what changed

For each installation: the version before and after, or "already up to date". Name anything that needs the user: a session restart for the plugin, a dirty tree that blocked a pull, a duplicate install still to resolve.

If new skills arrived, mention that `/ask-sk` is the router over the set, and that `/setup-sk-skills` is worth re-running in a repo only if a skill's setup expectations changed.
