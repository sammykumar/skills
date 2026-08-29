# SK Productions Skills

A collection of agent skills (slash commands and behaviors) loaded by Claude Code. Skills are organized into buckets and consumed by per-repo configuration emitted by `/setup-sk-skills`.

## Language

**Issue tracker**:
The tool that hosts a repo's issues: GitHub Issues, Linear, a Repo PDD Markdown convention (`docs/plans/`), or similar. Skills like `to-tickets`, `to-spec`, and `triage` read from and write to it.
_Avoid_: backlog manager, backlog backend, issue host

**Issue**:
A single tracked unit of work inside an **Issue tracker**: a bug, task, spec, or slice produced by `to-tickets`.
_Avoid_: ticket (use only when quoting external systems that call them tickets, or for a **Decision ticket**, see below)

**Decision ticket**:
A `wayfinder` unit: a child **Issue** of a `wayfinder:map` holding a *question* whose resolution is a decision, not a slice of a build to execute. The **decision** qualifier is what keeps it distinct from an implementation ticket; `wayfinder` introduces the term, then uses "ticket".

**Triage role**:
A canonical state-machine label applied to an **Issue** during triage (e.g. `needs-triage`, `ready-for-afk`). Each role maps to a real label string in the **Issue tracker** via `docs/agents/triage-labels.md`.

**Session transcript**:
The on-disk record of a past agent session: one JSONL file per session, written by Claude Code under `~/.claude/projects/<cwd-slug>/` and by Codex under `~/.codex/sessions/<Y>/<M>/<D>/`. Read-only input to `setup-sk-skills`; never written by any skill here.
_Avoid_: session log, chat history, conversation file

**User vocab**:
The language the user actually types, as distinct from the language the codebase is named in. Mined from **Session transcripts** and proposed as terms for `CONTEXT.md`. A single proposed item is just a *term*, unaccepted until the user confirms it.
_Avoid_: user's words, mined vocabulary, vocab corpus

## Relationships

- An **Issue tracker** holds many **Issues**
- An **Issue** carries one **Triage role** at a time
- A **Decision ticket** is an **Issue** (a child of a `wayfinder:map`)
- **User vocab** is mined from many **Session transcripts** and becomes terms in this glossary only once the user accepts them

## Flagged ambiguities

- "backlog" was previously used to mean both the *tool* hosting issues and the *body of work* inside it. Resolved: the tool is the **Issue tracker**; "backlog" is no longer used as a domain term.
- "backlog backend" / "backlog manager". Resolved: collapsed into **Issue tracker**.
