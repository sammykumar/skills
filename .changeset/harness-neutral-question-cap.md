---
"sk-skills": patch
---

grilling: state the structured-user-input cap in harness-neutral terms. The rule previously read "a call caps at four questions, four options each", which are Claude Code's `AskUserQuestion` numbers; on a harness whose tool takes fewer (Codex takes three) that reads as the size of a round, so the frontier gets silently truncated to one call. It now says every such tool caps a call, names four-by-four as Claude Code's specific case, and repeats that the cap bounds the call and never the round: keep calling until the whole frontier is covered, then wait.

Same pass over the fact-finding rule: "dispatch a sub-agent to find it" was a capability assumption stated with no fallback, so a harness without sub-agents got an instruction it cannot follow. It now reads as go and find the fact yourself, dispatching a sub-agent where the harness has them, with the non-blocking behaviour unchanged.
