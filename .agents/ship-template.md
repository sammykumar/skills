<!--
Canonical /ship template. Do NOT wire this file up as a live command; it is the
source the per-repo commands are cut from.

To instantiate in a repo, run from this repo:
  scripts/scaffold-ship.sh /path/to/target-repo [default-branch]

That copies everything below the marker line into <target-repo>/.claude/commands/ship.md,
substitutes {{DEFAULT_BRANCH}} (auto-detected from the target repo when the arg is
omitted), and leaves the two `REPO:` fill-in zones as TODOs. Then edit the target's
ship.md: fill the GATES and DEPLOY zones with that repo's real checks and deploy
story, adjust the frontmatter description / argument-hint, and set the commit-message
convention.

Everything above this line is stripped by the scaffold. The command body starts below.
-->
=== SHIP COMMAND BODY BELOW ===
---
description: Commit the work, push a branch, open a PR, merge it, fast-forward the default branch locally, and clean up branches.
argument-hint: [commit-only | no-ci] (default: branch to PR, merge, ff local, cleanup)
---

Ship the current work. `$ARGUMENTS` picks the path; default is **branch to PR, merge to `{{DEFAULT_BRANCH}}`, fast-forward local `{{DEFAULT_BRANCH}}`, clean up branches**.

- `commit-only`: commit, do not push or open a PR. Stop and report the SHAs.
- `no-ci`: open the PR and merge without waiting for checks. Only when you asked.

<!-- REPO: extra argument paths (e.g. `push` straight to the default branch, a `patch|minor|major` release bump). Delete this line if none. -->

## 1. Gates before committing

<!-- REPO: GATES START
Replace this block with the repo's real pre-commit gates: the build/lint/test
commands that actually catch this repo's expensive mistakes, and any manifest or
version checks. Name the command AND why it matters when the "why" is non-obvious
(the notes are the point). If the repo has no build or test step, say so here.
   REPO: GATES END -->

Report actual results. If a gate fails, fix it or stop and say so; do not ship past it silently.

## 2. Commit

Split the working tree into logical commits along natural boundaries, not one mega-commit. Use the repo's commit-message convention. <!-- REPO: name it, e.g. `type: subject` (feat:/fix:/docs:) or `<emoji> (<scope>): <imperative verb>`. -->

Attribution: write commits and the PR as if Sam authored them. No `Co-Authored-By`, no "Generated with", no 🤖, no mention of Claude/Anthropic/AI anywhere in the subject, body, PR title, or description. Strip any trailer a tool inserts.

## 3. Branch, push, PR, merge

If HEAD is `{{DEFAULT_BRANCH}}`, branch first. Branch from `origin/{{DEFAULT_BRANCH}}`, **never from HEAD** (branching off a just-merged branch produces a conflicting PR with no checks). Push the branch to `origin`, then:

```
gh pr create --base {{DEFAULT_BRANCH}} --fill
gh pr merge --merge   # a merge commit, not a squash
```

`no-ci` skips waiting on checks. Otherwise let required checks finish before merging.

## 4. Fast-forward the default branch locally, clean up branches

After the merge lands on the remote:

```
git checkout {{DEFAULT_BRANCH}}
git fetch origin
git merge --ff-only origin/{{DEFAULT_BRANCH}}   # fast-forward local to the merge
git branch -d <feature-branch>                  # delete the local branch (merged, so -d is safe)
git fetch --prune                               # drop the remote-tracking ref if the remote branch is gone
```

If `gh pr merge` did not delete the remote branch, delete it by hand (`git push origin --delete <feature-branch>`). Verify `git status` shows `{{DEFAULT_BRANCH}}` up to date with `origin/{{DEFAULT_BRANCH}}` and the feature branch gone locally and remotely.

<!-- REPO: DEPLOY START
If the repo deploys from the default branch, add the confirm-the-deploy steps
here: which target deploys (Vercel, workers, a tag release), what to watch, and
what to poll. A green PR check is not evidence: verify, do not infer. Include any
release-only or post-deploy steps (version bump, tracker updates). Delete this
whole zone if shipping ends at the merge.
   REPO: DEPLOY END -->

## 5. Report

State what shipped, the branch and PR, the SHAs, the gate results, and that local `{{DEFAULT_BRANCH}}` fast-forwarded and the branches were cleaned up. If a step failed, say so with the output.
