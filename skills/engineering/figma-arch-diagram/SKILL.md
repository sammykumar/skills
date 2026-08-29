---
name: figma-arch-diagram
description: Use when building or updating an architecture, tech-stack, networking, or data-flow diagram on a FigJam board from the "Icon Lib - Editable" component library, including asks like "diagram this stack", "map this pipeline", "show how these services connect", or updating a diagram already on a board. Places cards from the published library by component key, connects them with native FigJam connectors using explicit magnets, and verifies the result before calling it done. Do NOT use for Mermaid or the generate_diagram tool.
---

# figma-arch-diagram

## The governing rule

**Nothing is ever placed by hand.** Not by you, not by a subagent. A diagram is authored as a spec, coordinates are computed by `scripts/layout.mjs`, and Figma receives only already-solved numbers. Freehand placement is what produced the messy diagrams this skill exists to replace: connectors through labels, ragged rows, fan-outs cutting back across the canvas.

If you find yourself setting an `x`/`y` you reasoned about rather than one the engine returned, stop.

## The four stages

**1. Spec.** Author a diagram spec and normalize it with `scripts/spec.mjs`. The contract, every field, every validation error, and a worked example are in [references/spec-format.md](references/spec-format.md). `examples/e2e-tracking.json` is a real one.

**2. Layout.** `layout(spec, cardConstants)` from `scripts/layout.mjs` returns absolute coordinates for cards, notes, edges, sections and gutter annotations. Pure, no Figma, 38 unit tests. Run them with `node --test` from `scripts/` before trusting a change.

**3. Emit.** Build the board from the placement. Recipes that have actually been run are in [references/emit-recipes.md](references/emit-recipes.md).

**4. Verify.** Run the assertions in [references/verify.md](references/verify.md), then **look at the rendered board**. Not optional: stage 4 is what makes output reliably clean instead of usually clean.

## Prerequisites

The card library is a published Figma component library, "Icon Lib - Editable" (file key `oGJ5pTR4dQI0EJhKDvdELz`). Without access to it, `importComponentByKeyAsync` fails and no card can be placed. You also need the Figma MCP server connected, since every emit and verify step runs through it.

## Hard constraints

- **FigJam only** (`figma.com/board/...`). `figma.createPage()` is Design-only and throws here. Organize with FigJam sections.
- **Place cards by component key, never node id.** `figma.importComponentByKeyAsync(key).createInstance()`. All 121 keys are in [references/component-keys.json](references/component-keys.json). Node ids do not resolve across files. Requires the library to be published.
- **Never use an `AUTO` magnet.** `AUTO` lets Figma route a connector through a text label, the original bug. Flow edges are `RIGHT`→`LEFT` (LR) or `BOTTOM`→`TOP` (TB); sub-lane drops are `BOTTOM`→`TOP`; cross-row hops are `BOTTOM`→`LEFT`.
- **A new connector's `text.fontName` is invalid.** Loading it throws. Load a known font, assign `connector.text.fontName`, then set `characters`. Setting `connector.name` is invisible on canvas.
- **`ShowDetail` must be set before reading the `Detail` node**: while false the node does not exist. Discover the property key by prefix; its suffix differs between the source component and imported instances.
- **Drive `ShowDetail` from `card.height`, not from whether detail text exists**, otherwise a row with one detail card emits ragged heights, which is the defect the library normalization removed.
- **Text overflow is only visible via `absoluteRenderBounds`.** A wrapping text node keeps its declared size.
- **Connector paths cannot be inspected.** No `absoluteRenderBounds`, no polyline, and the bbox includes the label. Crossing checks are visual only.

## Plugin API mechanics

Do not restate them. Read `figma-use` and `figma-use-figjam` first: call the Skill tool with each name where they are registered, and where they are not, read them from the Figma plugin's cache directory on disk (`figma/<version>/skills/figma-use/SKILL.md` and `.../figma-use-figjam/SKILL.md`, with reference files in their sibling `references/` directories). `create-connector.md` and `create-section.md` are the relevant ones.

## Library reference

[references/library-map.md](references/library-map.md) lists all 13 category sets and 117 brands. [references/brand-samples.json](references/brand-samples.json) holds the per-brand placeholder for the instance band. [references/card-constants.json](references/card-constants.json) is the locked geometry: read it, never retype 140/192/284.
