---
"sk-skills": patch
---

`setup-sk-skills` can now seed `CONTEXT.md` from the vocabulary in your past sessions. A new opt-in Section D mines Claude Code transcripts and Codex rollouts for the repo you run it in (worktrees included), ranks the phrases you actually type by how many separate sessions they span and whether the codebase uses them too, clusters near-synonyms into proposed `_Avoid_` lines, and writes only the terms you confirm. The miner writes nothing itself: the shortlist goes to stdout, and terms already in your glossary are filtered before you see them, so re-running setup is additive.
