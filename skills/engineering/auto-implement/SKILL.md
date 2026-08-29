---
name: auto-implement
description: "Drive the whole idea-to-ship flow on a feature you name up front: grill it, record the design, then either build it here or split it into tickets."
disable-model-invocation: true
---

# Auto Implement

The main flow, driven end to end, entered with the feature already named. The user typed `/auto-implement <feature>`; whatever followed the command is the **starting idea**. If nothing followed it, ask what they want to build before doing anything else.

This skill runs the same route `ask-sk` maps, without stopping to ask which skill comes next. Run the phases in order. Do not skip ahead: each phase's output is the next one's input.

## What this skill may call

Every step below names a skill to pass to the Skill tool. Those names are exact. Do **not** substitute a `/`-prefixed flow name you may know for the same phase (`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`): those are user-invoked wrappers, the harness will refuse the call, and the turn is wasted. Call the skills named here.

## 1. Grill the idea

Call the Skill tool three times, for "grilling", "domain-modeling", and "recording-designs".

Interview the user about the starting idea until the design is sharp. `domain-modeling` keeps `CONTEXT.md` a glossary and writes ADRs for the hard-to-reverse calls; `recording-designs` puts the resolved design where this repo keeps plans.

If a question needs a runnable answer (a state model, business logic, a UI you have to see) rather than an argued one, call the Skill tool with "prototype" to settle it, then fold the answer back into the design and carry on grilling.

Do not `/clear` or `/compact` anywhere in this skill. Phases 1 to 3 build on each other and have to share one context window.

## 2. Pick the branch

When the grilling settles, decide with the user whether this is a **multi-session build**: more work than one fresh context window can hold and still reason sharply.

- Judge it by the design you just settled, not by the size of the original ask.
- Say which way you are leaning and why, then let the user overrule you.

Single session goes to phase 3a. Multi-session goes to phase 3b.

## 3a. Single session: build it here

Build the feature in this context window.

1. Call the Skill tool with "tdd" and build the work one red-green slice at a time, at the seams the grilling agreed on.
2. Run typechecking and single test files as you go; run the full suite once at the end.
3. Call the Skill tool with "code-review" to review the diff on both axes before committing.
4. Commit to the current branch.

Then stop and report what landed.

## 3b. Multi-session: spec, then tickets

1. Call the Skill tool with "writing-specs" to synthesize the settled design into a spec and publish it. No interview here: the grilling already happened.
2. Call the Skill tool with "splitting-tickets" to break the spec into tracer-bullet tickets with their blocking edges, published to the configured tracker.

Then **stop**. Do not start building.

Report the tickets, which ones have no blockers and can be grabbed now, and tell the user to work them one at a time: `/clear`, then `/implement <ticket>`, one fresh context window per ticket. Each ticket is self-contained by construction, so the last one's context is disposable. Building them here instead would carry this window's context into every ticket, which is the thing the ticket split exists to avoid.

## Preconditions

Phase 3b publishes to the project issue tracker and applies triage labels, so the tracker and label vocabulary should have been provided to you. If not, tell the user to run `/setup-sk-skills`.
