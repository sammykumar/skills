#!/usr/bin/env node
// Fails if an em-dash appears in the repo's prose. See CLAUDE.md for the rule.
// Runs as part of `npm run version`, right after `changeset version` regenerates
// CHANGELOG.md from the changesets, which is where these get in.
//
// Code is exempt, because a name quoted from another system has to stay verbatim:
// in Markdown, fenced blocks and inline code spans are stripped before checking.

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..");
const EM_DASH = String.fromCharCode(0x2014); // built from the code point so this file is not its own hit

const tracked = execFileSync("git", ["ls-files", "-z", "*.md", "*.mjs", "*.sh"], {
  cwd: repo,
  encoding: "utf8",
})
  .split("\0")
  .filter(Boolean);

// Blank out fenced blocks and inline code spans so only prose is left to check.
const proseOnly = (text) => {
  let fenced = false;
  return text.split("\n").map((line) => {
    if (/^\s*(```|~~~)/.test(line)) {
      fenced = !fenced;
      return "";
    }
    if (fenced) return "";
    return line.replace(/`[^`]*`/g, "");
  });
};

const hits = [];
let checked = 0;
for (const file of tracked) {
  const path = join(repo, file);
  // `git ls-files` lists the index, so a file deleted but not yet staged is still
  // tracked. `changeset version` consumes the changesets that way, and reading one
  // back would crash the check with ENOENT.
  if (!existsSync(path)) continue;
  checked += 1;
  const text = readFileSync(path, "utf8");
  const lines = file.endsWith(".md") ? proseOnly(text) : text.split("\n");
  lines.forEach((line, i) => {
    if (line.includes(EM_DASH)) hits.push(`${file}:${i + 1}`);
  });
}

if (hits.length === 0) {
  console.log(`no em-dashes in prose (${checked} files checked)`);
  process.exit(0);
}

console.error(`em-dashes found in ${hits.length} place(s):\n`);
for (const hit of hits) console.error(`  ${hit}`);
console.error(
  `\nRewrite each sentence with a comma, colon, period, parentheses, or a conjunction,` +
    `\nwhichever the sentence wants. Do not substitute the character blindly.`,
);
process.exit(1);
