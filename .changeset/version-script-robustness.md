---
"sk-skills": patch
---

Make `npm run version` survive a real release. The em-dash check now skips tracked files that no longer exist on disk, so it stops crashing with ENOENT on the changesets `changeset version` has just consumed, and a new `scripts/changeset-version.mjs` borrows a `GITHUB_TOKEN` from `gh auth token` when the variable is unset.
