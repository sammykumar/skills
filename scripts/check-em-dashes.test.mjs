import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// The checker resolves its repo from its own location, so each case gets a throwaway
// git repo with a copy of the script under scripts/, mirroring the real layout.
const source = join(dirname(fileURLToPath(import.meta.url)), "check-em-dashes.mjs");
const EM_DASH = String.fromCharCode(0x2014);

const scratch = (files) => {
  const root = mkdtempSync(join(tmpdir(), "em-dash-"));
  mkdirSync(join(root, "scripts"));
  copyFileSync(source, join(root, "scripts", "check-em-dashes.mjs"));
  for (const [name, body] of Object.entries(files)) {
    mkdirSync(dirname(join(root, name)), { recursive: true });
    writeFileSync(join(root, name), body);
  }
  const git = (...args) => execFileSync("git", args, { cwd: root, stdio: "ignore" });
  git("init", "-q");
  git("add", "-A");
  git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init");
  return root;
};

const run = (root) =>
  spawnSync(process.execPath, [join(root, "scripts", "check-em-dashes.mjs")], { encoding: "utf8" });

test("passes on prose without em-dashes", () => {
  const root = scratch({ "README.md": "Plain prose, no dashes.\n" });
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  rmSync(root, { recursive: true, force: true });
});

test("fails on an em-dash in prose", () => {
  const root = scratch({ "README.md": `A sentence ${EM_DASH} with a dash.\n` });
  const result = run(root);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /README\.md:1/);
  rmSync(root, { recursive: true, force: true });
});

test("ignores a tracked file that no longer exists on disk", () => {
  // What `changeset version` leaves behind: the consumed changesets are deleted
  // from the working tree but still listed by `git ls-files`.
  const root = scratch({ ".changeset/some-change.md": "A changeset.\n", "README.md": "Fine.\n" });
  rmSync(join(root, ".changeset", "some-change.md"));
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  // The copied checker is tracked too, so the surviving pair is README.md and the script.
  assert.match(result.stdout, /2 files checked/);
  rmSync(root, { recursive: true, force: true });
});
