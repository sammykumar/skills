## What it does

`update-sk-skills` brings the skills on this machine up to date. It never assumes how they got here: it reads the evidence on disk first, then runs the update command that matches what it found.

That is the whole point of the skill. There are three routes in (the Claude Code plugin, skills.sh, and a symlinked dev checkout of the repo) and each is updated by a different command, so an updater that guesses is wrong a third of the time. The harness you are in does not settle it either: Claude Code users are on the plugin route or the skills.sh route depending on which one they picked at install time, and a machine can carry more than one at once.

## When to reach for it

You invoke this by typing `/update-sk-skills`; the agent won't reach for it on its own.

Reach for it when you want the newer skills: a changelog entry you read, a skill that behaves differently from how the docs describe it, or just periodic upkeep. For configuring a repo to *use* the skills, which is a different job entirely and runs once per repo, use [setup-sk-skills](../engineering/setup-sk-skills.md).

## The three routes

Each leaves its own fingerprint, and the skill looks for all of them before acting rather than stopping at the first hit.

| Route | What it looks for | How it updates |
| --- | --- | --- |
| **Claude Code plugin** | an `sk-skills@<marketplace>` entry in the installed-plugins record, with its scope and version | refresh the marketplace, then update the plugin at the scope it is installed at |
| **skills.sh** | a lockfile entry whose source is `sammykumar/skills`, global or project-scoped | update those skills by name, in that scope |
| **Dev checkout** | the skill directory is a symlink into a git working tree of the repo | pull the checkout, then relink |
| **Hand-copied files** | real directories, no lockfile entry, no plugin record | nothing automatic; adopt one of the two supported routes |

Three findings get reported rather than acted on. A **dev checkout with a dirty tree** is never pulled under your work. A **plugin installed but disabled** in this repo is up to date and still not running, which is worth knowing before you wonder why nothing changed. And **both routes present at once** is a duplicate install, not a two-for-one: the plugin's copy and the skills.sh copy of the same skill both load, with no way to tell which is running, so the skill stops and asks which one to keep.

## Common questions

**Why did nothing change after it said the plugin updated?**

A plugin update lands on disk but does not apply to a running session. Restart the session. The skill says so in its report, and the underlying CLI says the same thing in its own output.

**The two routes report different versions. Which one is right?**

Both, for different definitions. The plugin installs a released version from the marketplace; skills.sh installs what is on `main`, which includes changes merged since the last release. Someone on the skills.sh route can be running skills that no released version contains yet. This has been raised directly as an issue, and it is a property of the two distribution routes rather than a bug in either.

**Will it overwrite the edits I made to a skill?**

On the skills.sh route, yes: an update rewrites the skill files, and the whole premise of that route is that the files are yours to edit. The skill flags local modifications it can see before running, but the safe habit is to keep your changes in a fork you install from. The plugin route is read-only, so there is nothing to overwrite.

**Do I need to re-run `/setup-sk-skills` afterwards?**

Only if a skill's setup expectations changed. The config in `docs/agents/` is per-repo and outlives updates. The seed templates it was written from do change between versions, so if a skill starts describing your tracker differently from how your `docs/agents/issue-tracker.md` reads, re-running setup is the cheap fix.

**Why is this a skill rather than a slash command file?**

A command file in `.claude/commands/` exists only in the repo that carries it, and a plugin-distributed command never reaches Codex. Shipping it as a user-invoked skill is what makes `/update-sk-skills` available on both harnesses and on both installation routes.

## It's working if

- Before running anything, it shows you a table of what it found and the exact commands it proposes.
- The route it names matches how you actually installed the skills, including when that is a symlinked checkout rather than an installer.
- After a plugin update it tells you to restart the session, rather than leaving you to notice.
- On a machine carrying both routes it stops and asks, instead of updating both and leaving the duplicates in place.
- Afterwards, a skill you knew had changed reads the new way.

## Where it fits

`update-sk-skills` is **periodic maintenance** on the skills themselves, off every flow. Its one neighbour is [setup-sk-skills](../engineering/setup-sk-skills.md), the run-once setup that points the skills at a repo's tracker and docs: that one configures how the skills read *this repo*, this one changes which version of the skills you are running everywhere. For which skill to reach for next, [ask-sk](../engineering/ask-sk.md) routes the whole set.
