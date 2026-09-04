import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// The adapter is Python, because it reuses the vendored Python renderer. Driving
// it through `--map-only` tests the payload translation, which is the part that
// carries logic, without asserting on ANSI output that is expected to change
// whenever the renderer's layout does.
const here = dirname(fileURLToPath(import.meta.url));
const adapter = join(here, "scripts", "copilot-statusline.py");

// Captured from a live GitHub Copilot CLI 1.0.82 session, not hand-written, so
// the field names here are the ones Copilot really sends.
const fixture = JSON.parse(readFileSync(join(here, "test", "copilot-payload.json"), "utf8"));

const map = (payload) =>
  JSON.parse(
    execFileSync("python3", [adapter, "--map-only"], {
      input: JSON.stringify(payload),
      encoding: "utf8",
    }),
  );

test("maps the fields Copilot and Claude Code share", () => {
  const out = map(fixture);
  assert.equal(out.session_id, "20e45d57-15c5-42c1-a795-a255b4cb3fc7");
  assert.equal(out.cwd, "/Users/samkumar/Development/SK-Productions-LLC/skills");
  assert.equal(out.version, "1.0.82");
  assert.equal(out.cost.total_lines_added, 12);
  assert.equal(out.cost.total_lines_removed, 3);
});

test("splits Copilot's combined model name into model and effort", () => {
  const out = map(fixture);
  assert.equal(out.model.display_name, "gpt-5.6-sol");
  assert.equal(out.model.id, "gpt-5.6-sol");
  assert.equal(out.effort.level, "medium");
  // The renderer only shows an effort level when thinking is enabled.
  assert.equal(out.thinking.enabled, true);
});

test("a model name with no effort suffix leaves effort empty", () => {
  const out = map({ ...fixture, model: { id: "gpt-5.6-sol", display_name: "gpt-5.6-sol" } });
  assert.equal(out.model.display_name, "gpt-5.6-sol");
  assert.equal(out.effort.level, "");
  assert.equal(out.thinking.enabled, false);
});

test("prefers live context usage over the cumulative session figure", () => {
  const out = map(fixture);
  // used_percentage is 8 (cumulative); current_context_used_percentage is 7.88.
  assert.equal(out.context_window.used_percentage, 7.88);
});

test("falls back to cumulative usage when the live figure is absent", () => {
  const context = { ...fixture.context_window };
  delete context.current_context_used_percentage;
  const out = map({ ...fixture, context_window: context });
  assert.equal(out.context_window.used_percentage, 8);
});

test("uses the displayed context limit as the window size", () => {
  const out = map({
    ...fixture,
    context_window: { ...fixture.context_window, displayed_context_limit: 128000 },
  });
  assert.equal(out.context_window.context_window_size, 128000);
  assert.equal(out.exceeds_200k_tokens, false);
});

test("synthesises current usage when Copilot omits the breakdown", () => {
  const out = map(fixture);
  assert.deepEqual(out.context_window.current_usage, {
    input_tokens: 31500,
    output_tokens: 17,
    cache_creation_input_tokens: 13500,
    cache_read_input_tokens: 18000,
  });
});

test("passes through Copilot's own current_usage when present", () => {
  const out = map({
    ...fixture,
    context_window: {
      ...fixture.context_window,
      current_usage: {
        input_tokens: 1,
        output_tokens: 2,
        cache_creation_input_tokens: 3,
        cache_read_input_tokens: 4,
      },
    },
  });
  assert.equal(out.context_window.current_usage.input_tokens, 1);
  assert.equal(out.context_window.current_usage.cache_read_input_tokens, 4);
});

test("invents no dollar cost, because Copilot bills in AI credits", () => {
  const out = map(fixture);
  // ai_used.formatted is "3.76" credits; putting that in a USD field would
  // render a wrong number in a currency-labelled slot.
  assert.equal(out.cost.total_cost_usd, undefined);
});

test("omits rate limits, which Copilot does not report", () => {
  const out = map(fixture);
  assert.equal(out.rate_limits, undefined);
});

test("nulls become empty strings rather than the string 'null'", () => {
  const out = map({ ...fixture, session_name: null, transcript_path: null });
  assert.equal(out.session_name, "");
  assert.equal(out.transcript_path, "");
});

test("survives a payload with nothing but a cwd", () => {
  const out = map({ cwd: "/tmp" });
  assert.equal(out.cwd, "/tmp");
  assert.equal(out.model.display_name, "");
  assert.equal(out.context_window.context_window_size, 0);
  assert.equal(out.exceeds_200k_tokens, false);
});
