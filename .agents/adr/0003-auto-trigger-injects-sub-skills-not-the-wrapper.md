# The new-feature auto-trigger injects the grilling sub-skills, never grill-with-docs

To auto-start the grill-with-docs workflow on new-feature sessions, a `UserPromptSubmit` hook (on both Claude Code and Codex) classifies the prompt and injects context that tells the model to invoke the `grilling` and `domain-modeling` skills directly and record the design per the plan convention. It deliberately never names `grill-with-docs`, even though that is the skill we are trying to trigger.

## Why

`grill-with-docs` is `disable-model-invocation: true` (user-invoked by convention). That is a hard block: the model cannot call it, and on Claude Code, if injected context tells the model to invoke it, Claude Code blocks the call and instructs the model not to reproduce the steps another way, poisoning the turn. A hook also cannot execute a slash command or a skill on either platform: its only lever is injecting context the model then acts on. So the only path to auto-start is to have the hook inject the wrapper's *body*, invoking the two underlying skills, which are both model-invocable.

## Considered options

- **Flip `disable-model-invocation` on the wrapper** so a hook can nudge the model to call it. Rejected: it changes the skill's nature repo-wide, requires syncing `agents/openai.yaml`, and breaks the user-invoked convention, all to save duplicating a short instruction.
- **Point the injected context at the wrapper's files to read and follow.** Rejected: the file path contains `grill-with-docs`, and the injection fires in arbitrary repos, so it both risks the block trap and dangles.

## Consequences

The injected instruction duplicates the wrapper's body (invoke the two skills; inline the plan-location detection rules) and must be re-synced by hand if the wrapper or `PLAN-LOCATION.md` changes. This is the accepted cost of keeping the wrapper cleanly user-invoked and staying clear of the block trap.
