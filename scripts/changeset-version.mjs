#!/usr/bin/env node
// Runs `changeset version` with a GITHUB_TOKEN in the environment.
//
// The changelog generator (@changesets/changelog-github) resolves PR and author
// links through the GitHub API, so it aborts when GITHUB_TOKEN is unset. Releases
// here are cut by hand on a machine that already has an authenticated `gh` CLI,
// so borrow the token from `gh auth token` rather than making the human export one.
// The token is passed to the child process only; nothing writes it to disk.

import { execFileSync, spawnSync } from "node:child_process";

const ghToken = () => {
  try {
    return execFileSync("gh", ["auth", "token"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
};

const token = process.env.GITHUB_TOKEN || ghToken();

if (!token) {
  console.error(
    "changeset version needs a GitHub token to build the changelog links.\n" +
      "Either sign in with `gh auth login`, or export GITHUB_TOKEN with a personal\n" +
      "access token that has public_repo scope.",
  );
  process.exit(1);
}

const result = spawnSync("changeset", ["version"], {
  stdio: "inherit",
  env: { ...process.env, GITHUB_TOKEN: token },
  shell: false,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
