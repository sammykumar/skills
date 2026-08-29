import { test } from "node:test";
import assert from "node:assert/strict";

import {
  extractClaudeTurns,
  extractCodexTurns,
  parseGlossary,
  rankTerms,
  claudeSlug,
} from "./mine-vocab.mjs";

const claudeLines = (records) => records.map((r) => JSON.stringify(r)).join("\n");

test("claude: keeps plain typed turns", () => {
  const turns = extractClaudeTurns(
    claudeLines([
      { type: "user", message: { role: "user", content: "the lead profile drawer is stale" } },
    ]),
  );
  assert.deepEqual(turns, ["the lead profile drawer is stale"]);
});

test("claude: drops slash-command expansions, tool results and sidechains", () => {
  const turns = extractClaudeTurns(
    claudeLines([
      { type: "user", isMeta: true, message: { role: "user", content: [{ type: "text", text: "Ship the current work. Gates before committing..." }] } },
      { type: "user", message: { role: "user", content: [{ type: "tool_result", content: "ok" }] } },
      { type: "user", isSidechain: true, message: { role: "user", content: "explore the repo" } },
      { type: "assistant", message: { role: "assistant", content: "sure" } },
      { type: "user", message: { role: "user", content: "keep this one" } },
    ]),
  );
  assert.deepEqual(turns, ["keep this one"]);
});

test("claude: strips injected spans but keeps the words around them", () => {
  const turns = extractClaudeTurns(
    claudeLines([
      {
        type: "user",
        message: {
          role: "user",
          content:
            "<command-name>/ship</command-name><command-args>no-ci</command-args>ship the stuck lead sweeper<system-reminder>be careful</system-reminder>",
        },
      },
      {
        type: "user",
        message: { role: "user", content: "<local-command-stdout>lots of output</local-command-stdout>" },
      },
    ]),
  );
  assert.deepEqual(turns, ["ship the stuck lead sweeper"]);
});

test("codex: keeps typed turns and drops injected instruction blobs", () => {
  const turns = extractCodexTurns(
    claudeLines([
      { type: "session_meta", payload: { cwd: "/repo" } },
      {
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text: "# AGENTS.md instructions for /repo\n<INSTRUCTIONS>do things</INSTRUCTIONS>" }],
        },
      },
      {
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text: "<environment_context>cwd=/repo</environment_context>" }],
        },
      },
      {
        type: "response_item",
        payload: { type: "message", role: "assistant", content: [{ type: "output_text", text: "on it" }] },
      },
      {
        type: "response_item",
        payload: { type: "message", role: "user", content: [{ type: "input_text", text: "the stuck lead sweeper is double firing" }] },
      },
    ]),
  );
  assert.deepEqual(turns, ["the stuck lead sweeper is double firing"]);
});

test("glossary: reads accepted terms and their avoided synonyms", () => {
  const glossary = parseGlossary(`# Repo

## Language

**Issue tracker**:
Where issues live.
_Avoid_: backlog manager, backlog backend

**Triage role**:
A label.
`);
  assert.deepEqual(glossary.terms, ["issue tracker", "triage role"]);
  assert.deepEqual(glossary.avoided, ["backlog manager", "backlog backend"]);
});

test("ranking: a phrase used across sessions outranks one used as often in a single session", () => {
  const spread = ["stuck lead sweeper runs", "stuck lead sweeper again", "stuck lead sweeper fixed"];
  const ranked = rankTerms([
    [spread[0], "the nightly digest job fired", "the nightly digest job fired", "the nightly digest job fired"],
    [spread[1]],
    [spread[2]],
  ]);
  const terms = ranked.map((c) => c.term);
  assert.ok(terms.indexOf("stuck lead sweeper") < terms.indexOf("nightly digest job"));
  const sweeper = ranked.find((c) => c.term === "stuck lead sweeper");
  assert.equal(sweeper.sessions, 3);
  assert.equal(sweeper.count, 3);
  assert.ok(sweeper.evidence[0].includes("stuck lead sweeper"));
});

test("ranking: drops terms the glossary already accepted or already avoids", () => {
  const sessions = [
    ["the issue tracker is github", "the backlog manager is github", "the stuck lead sweeper broke"],
    ["the issue tracker is github", "the backlog manager is github", "the stuck lead sweeper broke"],
  ];
  const ranked = rankTerms(sessions, {
    glossary: { terms: ["issue tracker"], avoided: ["backlog manager"] },
  });
  const terms = ranked.map((c) => c.term);
  assert.ok(!terms.includes("issue tracker"));
  assert.ok(!terms.includes("backlog manager"));
  assert.ok(terms.includes("stuck lead sweeper"));
});

test("ranking: a phrase the codebase also uses outranks an equally common one it does not", () => {
  const sessions = [
    ["the lead profile drawer", "the queue backfill runner"],
    ["the lead profile drawer", "the queue backfill runner"],
  ];
  const ranked = rankTerms(sessions, { codeText: "class LeadProfileDrawer {}" });
  const drawer = ranked.find((c) => c.term === "lead profile drawer");
  const runner = ranked.find((c) => c.term === "queue backfill runner");
  assert.equal(drawer.inCode, true);
  assert.equal(runner.inCode, false);
  assert.ok(drawer.score > runner.score);
});

test("ranking: clusters synonyms on a shared head noun and proposes avoids", () => {
  const sessions = [
    ["the stuck lead sweeper ran", "the stuck lead sweeper ran", "the stale lead sweeper ran"],
    ["the stuck lead sweeper ran", "the stuck lead sweeper ran", "the stale lead sweeper ran"],
  ];
  const ranked = rankTerms(sessions);
  const dominant = ranked.find((c) => c.term === "stuck lead sweeper");
  assert.deepEqual(dominant.avoid, ["stale lead sweeper"]);
  assert.ok(!ranked.some((c) => c.term === "stale lead sweeper"));
});

test("claude slug: matches the project dir, and worktrees share its prefix", () => {
  const root = claudeSlug("/Users/sam/Development/SK/skills");
  assert.equal(root, "-Users-sam-Development-SK-skills");
  const worktree = claudeSlug("/Users/sam/Development/SK/skills/.claude/worktrees/finch");
  assert.ok(worktree.startsWith(root));
  assert.equal(claudeSlug("/Users/sam/perch/perch.martech"), "-Users-sam-perch-perch-martech");
});

test("claude: drops harness notifications that arrive as user records", () => {
  const turns = extractClaudeTurns(
    claudeLines([
      {
        type: "user",
        message: {
          role: "user",
          content:
            "<task-notification>\n<task-id>abc</task-id>\n<status>completed</status>\nsubagent tokens and tool uses\n</task-notification>",
        },
      },
      { type: "user", message: { role: "user", content: "<ide_diagnostics>lint noise</ide_diagnostics>" } },
      { type: "user", message: { role: "user", content: "<bash-input>ls</bash-input>" } },
      { type: "user", message: { role: "user", content: "the lead profile drawer is stale" } },
    ]),
  );
  assert.deepEqual(turns, ["the lead profile drawer is stale"]);
});

test("claude: drops bracketed harness markers", () => {
  const turns = extractClaudeTurns(
    claudeLines([
      { type: "user", message: { role: "user", content: "[Request interrupted by user for tool use]" } },
      { type: "user", message: { role: "user", content: "the lead profile drawer is stale" } },
    ]),
  );
  assert.deepEqual(turns, ["the lead profile drawer is stale"]);
});

test("ranking: evidence quotes do not repeat once truncated", () => {
  const long = `${"the stuck lead sweeper ".repeat(20)}tail`;
  const ranked = rankTerms([[long, `${long} but different past the cutoff`], [long]]);
  const sweeper = ranked.find((c) => c.term === "stuck lead sweeper");
  assert.equal(new Set(sweeper.evidence).size, sweeper.evidence.length);
});

test("claude: drops compaction and local-command preambles", () => {
  const turns = extractClaudeTurns(
    claudeLines([
      { type: "user", message: { role: "user", content: "This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion." } },
      { type: "user", message: { role: "user", content: "Caveat: The messages below were generated by the user while running local commands. DO NOT respond to these." } },
      { type: "user", message: { role: "user", content: "the lead profile drawer is stale" } },
    ]),
  );
  assert.deepEqual(turns, ["the lead profile drawer is stale"]);
});

test("ranking: punctuation runs are never candidate terms", () => {
  const ranked = rankTerms([["--- --- ---", "--- --- ---"], ["--- --- ---"]]);
  assert.deepEqual(ranked, []);
});

test("ranking: the glossary check folds simple plurals", () => {
  const sessions = [
    ["the session transcripts are big", "the queue backfill runner broke"],
    ["the session transcripts are big", "the queue backfill runner broke"],
  ];
  const ranked = rankTerms(sessions, { glossary: { terms: ["session transcript"], avoided: [] } });
  const terms = ranked.map((c) => c.term);
  assert.ok(!terms.includes("session transcripts"));
  assert.ok(terms.includes("queue backfill runner"));
});

test("ranking: the codebase witness sees file contents, not just paths", () => {
  const sessions = [
    ["the queue backfill runner broke", "the nightly digest mailer broke"],
    ["the queue backfill runner broke", "the nightly digest mailer broke"],
  ];
  const ranked = rankTerms(sessions, { codeText: "// runs the queue backfill runner every hour" });
  assert.equal(ranked.find((c) => c.term === "queue backfill runner").inCode, true);
  assert.equal(ranked.find((c) => c.term === "nightly digest mailer").inCode, false);
});
