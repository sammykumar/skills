---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round, each question carrying your recommended answer, then wait for the user's answers before the next round.

Ask the round through the harness's structured user-input tool whenever one exists (Claude Code exposes `AskUserQuestion`; other harnesses expose an equivalent request-for-input). Picking an answer beats quoting a question back, and it is what most users reach for. Map each frontier question onto it:

- One question per decision. Make your recommended answer the first option and suffix its label `(Recommended)`; list the other viable answers as the remaining options.
- The tool adds a free-form option itself, so list only the discrete answers. When more than one answer can hold at once, mark the question multi-select.
- Every such tool caps how many questions one call carries (Claude Code's `AskUserQuestion` takes four, with four options each; other harnesses have their own caps). Treat that cap as a limit on the call, never on the round. A frontier wider than the cap is consecutive calls inside the same round: keep calling until the whole frontier is covered, then wait. Never shrink the round to fit one call.
- A decision with no discrete answers to choose between (a name, an open-ended constraint) has nothing to select. Ask it in the prose format below.

Where the harness exposes no such tool, ask the whole round in prose, one question per block:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), go and find it yourself; don't ask the user for anything you could look up yourself. Where the harness can spawn a sub-agent, dispatch one so the search runs alongside the round. Either way, don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the answer; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
