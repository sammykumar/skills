---
description: Commit the work, push a branch, open a PR, merge it, fast-forward main locally, and clean up branches.
argument-hint: [commit-only | no-ci] (default: branch to PR, merge to main, ff local, cleanup)
---

Ship the current work. `$ARGUMENTS` picks the path; default is **branch to PR, merge to `main`, fast-forward local `main`, clean up branches**.

- `commit-only`: commit, do not push or open a PR. Stop and report the SHAs.
- `no-ci`: open the PR and merge without waiting for checks. Only when you asked.

## 1. Gates before committing

This repo has no build or test step; the gates are about the manifests and the prose rules in `CLAUDE.md`. Run only the ones your change touched:

- If you edited `.claude-plugin/plugin.json` or `.claude-plugin/marketplace.json`: `claude plugin validate . --strict`.
- If either manifest version or `package.json` version changed: `npm run check-plugin-version`.
- If this is a user-facing skill change: add a changeset with `npm run changeset` (do not hand-edit versions).
- No em-dashes anywhere in the repo's prose. If a promoted skill (`engineering/` or `productivity/`) was added, renamed, or changed, confirm its `README.md` entry, `plugin.json` skills array, `docs/<bucket>/<skill>.md` page, and `ask-sk` routing are all in sync before shipping a lie.

Report actual results. If a gate fails, fix it or stop and say so; do not ship past it silently.

## 2. Commit

Split the working tree into logical commits along natural boundaries, not one mega-commit. Use the repo's `type: subject` message style (e.g. `feat:`, `fix:`, `docs:`).

Attribution: write commits and the PR as if Sam authored them. No `Co-Authored-By`, no "Generated with", no 🤖, no mention of Claude/Anthropic/AI anywhere in the subject, body, PR title, or description. Strip any trailer a tool inserts.

## 3. Branch, push, PR, merge

If HEAD is `main`, branch first. Branch from `origin/main`, **never from HEAD** (branching off a just-merged branch produces a conflicting PR with no checks). Push the branch to `origin`, then:

```
gh pr create --base main --fill
gh pr merge --merge   # a merge commit, not a squash
```

`no-ci` skips waiting on checks. Otherwise let required checks finish before merging.

## 4. Fast-forward main locally, clean up branches

After the merge lands on the remote:

```
git checkout main
git fetch origin
git merge --ff-only origin/main   # fast-forward local main to the merge
git branch -d <feature-branch>    # delete the local branch (merged, so -d is safe)
git fetch --prune                 # drop the remote-tracking ref if the remote branch is gone
```

If `gh pr merge` did not delete the remote branch, delete it by hand (`git push origin --delete <feature-branch>`). Verify `git status` shows `main` up to date with `origin/main` and the feature branch gone locally and remotely.

## 5. Report

State what shipped, the branch and PR, the SHAs, the gate results, and that local `main` fast-forwarded and the branches were cleaned up. If a step failed, say so with the output.
