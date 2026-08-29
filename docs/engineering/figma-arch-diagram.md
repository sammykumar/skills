## What it does

`figma-arch-diagram` builds an architecture, tech-stack, networking, or data-flow diagram on a FigJam board out of a published component library, then checks the result before calling it done. Nothing on the board is ever placed by hand: the diagram is authored as a spec, every coordinate is computed by a tested layout engine, and Figma receives only already-solved numbers.

That constraint is the whole skill. Freehand placement is what produced the diagrams it exists to replace, the ones with connectors running through text labels, rows that drift out of line, and fan-outs cutting back across the canvas. An agent that reasons its way to an `x` and a `y` reproduces all three, so the skill removes the opportunity.

## When to reach for it

Type `/figma-arch-diagram`, or the agent reaches for it automatically when a task turns into drawing a system on a board.

Reach for it when the diagram is going onto a FigJam board and is made of real components: services, frameworks, data stores, third-party tools. What you want decides which tool:

| What you want | Reach for |
| --- | --- |
| A branded architecture diagram on a FigJam board | `figma-arch-diagram` |
| A diagram inline in a Markdown file or a PR | Mermaid, written by hand |
| A quick sketch on a board, no library, no layout discipline | the Figma MCP server's `generate_diagram` |
| An existing Figma design turned into code | the Figma plugin's own `figma-use` skills |

It also handles updating a diagram already on a board, which is the more common case once a stack has been drawn once.

## Prerequisites

Two things have to be in place, and neither is optional:

- **The published component library.** Cards come from "Icon Lib - Editable" (file key `oGJ5pTR4dQI0EJhKDvdELz`), placed by component key. Without access to that library, `importComponentByKeyAsync` fails and no card can be placed at all. This is the one skill in the set that does not run anywhere.
- **The Figma MCP server, connected.** Every emit and verify step runs through it, against a FigJam board (`figma.com/board/...`), never a Design file.

## Spec, layout, emit, verify

The four stages are the skill's spine, and the split is what makes the output repeatable:

| Stage | What happens | Where it lives |
| --- | --- | --- |
| Spec | You author the diagram as data: rows, nodes, edges, notes | `references/spec-format.md` |
| Layout | A pure function turns the spec into absolute coordinates | `scripts/layout.mjs`, 38 unit tests |
| Emit | Cards are placed by component key, connectors by explicit magnet | `references/emit-recipes.md` |
| Verify | Assertions run, then a human looks at the render | `references/verify.md` |

Layout is pure and knows nothing about Figma, which is why it can be tested at all. That is where a placement bug gets fixed: if a card lands in the wrong place, the fix goes into the engine and the board is re-emitted, never nudged in Figma.

Stage 4 is the one that gets skipped and shouldn't be. Some defects are only visible in the render, because the Plugin API will not report them: a text node keeps its declared size when its text overflows, and a connector exposes no route at all, so whether a line crosses a card is a question only your eyes can answer.

## Common questions

**Why not Mermaid, or the `generate_diagram` tool?**

Different output. Both of those produce a diagram; this produces a branded board built from your own component library, laid out to fixed geometry, that someone can present. If a code-adjacent sketch is what you need, Mermaid is faster and belongs in the repo where the reader already is.

**Cross-row connectors still cross other content. Is that a bug?**

It is a known, recorded limit rather than a surprise. Cross-row routing is the one case the engine does not fully solve: a reserved vertical channel keeps the long run clear, but the horizontal legs at either end can still cut across content. The recipes record what was measured and rule out fixing it in the emitter by nudging magnets. The real fix belongs in the layout engine, by deriving the row gap from the deepest card above it instead of using a fixed constant.

**Can I just let the model place a few cards, for a small diagram?**

No, and small diagrams are where the temptation is highest. The layout engine is also what holds the row baseline, the reserved detail bands, and the connector magnets consistent, so a hand-placed card is not a small exception to the rule; it is the row it sits in going ragged.

## It's working if

- Every card in a row shares a top edge and a bottom edge, including cards with nothing in their detail band.
- Labelled connectors run straight between cards rather than elbowing around them, and none passes through a text label.
- Row titles are visible in the render, not just in the layers panel.
- When something is wrong, the fix is a re-run: you change the spec or the engine and re-emit, rather than dragging anything on the board.
- `node --test` in `scripts/` is green before you trust a layout change.

## Where it fits

A reach-for-it-anytime standalone. It sits outside the build chain: nothing invokes it and it invokes nothing, though it reads the Figma plugin's own `figma-use` and `figma-use-figjam` skills for Plugin API mechanics rather than restating them. In practice it shows up beside the thinking skills, when a system that has just been designed or diagnosed needs to be shown to someone. For the map of the whole set, see [ask-sk](../engineering/ask-sk.md).
