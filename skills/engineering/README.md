# Engineering

Skills I use daily for code work.

## User-invoked

Reachable only when you type them (Claude Code: `disable-model-invocation: true`; Codex: `policy.allow_implicit_invocation: false` in `agents/openai.yaml`).

- **[ask-sk](./ask-sk/SKILL.md)**: Ask which skill or flow fits your situation. A router over the user-invoked skills in this repo.
- **[auto-implement](./auto-implement/SKILL.md)**: Drive the whole idea-to-ship flow on a feature you name up front: grill it, record the design, then either build it here or split it into tickets.
- **[grill-with-docs](./grill-with-docs/SKILL.md)**: Grilling session that also documents as it goes: sharpening terminology in `CONTEXT.md`, recording hard decisions as ADRs, and writing the resolved design into your repo's planning-doc location.
- **[triage](./triage/SKILL.md)**: Move issues through a state machine of triage roles.
- **[improve-codebase-architecture](./improve-codebase-architecture/SKILL.md)**: Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
- **[setup-sk-skills](./setup-sk-skills/SKILL.md)**: Configure this repo for the engineering skills (issue tracker, triage labels, domain doc layout), and seed `CONTEXT.md` from the vocabulary in your past sessions. Run once per repo.
- **[update-sk-skills](./update-sk-skills/SKILL.md)**: Update the skills on this machine, after detecting how they were actually installed: the Claude Code plugin, skills.sh, or a dev checkout.
- **[to-spec](./to-spec/SKILL.md)**: Turn the current conversation into a spec and publish it to the issue tracker.
- **[to-tickets](./to-tickets/SKILL.md)**: Break any plan, spec, or conversation into a set of tracer-bullet tickets, each declaring its blocking edges, whether as text in a local file or as native blocking links on a real tracker.
- **[implement](./implement/SKILL.md)**: Build the work described by a spec or set of tickets, driving `/tdd` at pre-agreed seams and closing out with `/code-review` before committing.
- **[wayfinder](./wayfinder/SKILL.md)**: Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on the issue tracker, resolved one at a time until the way to the destination is clear.

## Model-invoked

Model- or user-reachable (rich trigger phrasing so the model can reach for them).

- **[prototype](./prototype/SKILL.md)**: Build a throwaway prototype to answer a design question: a single shareable HTML file for state/logic, or several toggleable UI variations.

- **[diagnosing-bugs](./diagnosing-bugs/SKILL.md)**: Disciplined diagnosis loop for hard bugs and performance regressions: build a feedback loop that goes red on this bug → minimise → hypothesise → instrument → fix → regression-test.
- **[research](./research/SKILL.md)**: Investigate a question against high-trust primary sources and capture the findings as a cited Markdown file in the repo, run as a background agent.
- **[tdd](./tdd/SKILL.md)**: Test-driven development with a red-green-refactor loop. Builds features or fixes bugs one vertical slice at a time.
- **[domain-modeling](./domain-modeling/SKILL.md)**: Actively build and sharpen a project's domain model by challenging terms, stress-testing with scenarios, and updating `CONTEXT.md` and ADRs inline.
- **[codebase-design](./codebase-design/SKILL.md)**: Shared discipline and vocabulary for designing deep modules: small interfaces, clean seams, testable through the interface.
- **[code-review](./code-review/SKILL.md)**: Two-axis review of the diff since a fixed point: **Standards** (does it follow the repo's coding standards, plus a Fowler smell baseline?) and **Spec** (does it faithfully implement the originating issue/spec?), run as parallel sub-agents.
- **[resolving-merge-conflicts](./resolving-merge-conflicts/SKILL.md)**: Work through an in-progress git merge or rebase conflict hunk by hunk, resolving by intent traced to each side's primary source, then finish the operation, never `--abort`.
- **[wizard](./wizard/SKILL.md)**: Generate an interactive bash wizard that walks a human through steps only they can perform: provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover.
- **[writing-specs](./writing-specs/SKILL.md)**: Synthesize the current conversation into a spec and publish it to the project issue tracker. The engine under `/to-spec`.
- **[splitting-tickets](./splitting-tickets/SKILL.md)**: Break a plan, spec, or conversation into tracer-bullet tickets with their blocking edges, published to the configured tracker. The engine under `/to-tickets`.
- **[recording-designs](./recording-designs/SKILL.md)**: Write the resolved design record into whatever planning-doc convention the repo already uses. The engine `/grill-with-docs` and `/auto-implement` share.
- **[figma-arch-diagram](./figma-arch-diagram/SKILL.md)**: Build or update an architecture, tech-stack, networking, or data-flow diagram on a FigJam board from the "Icon Lib - Editable" component library, authored as a spec and laid out by a tested engine so nothing is placed by hand.
