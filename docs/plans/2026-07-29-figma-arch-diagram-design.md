# Figma architecture diagrams: library normalization + generation skill

Status: implemented and shipped. The skill lives at [`skills/engineering/figma-arch-diagram/`](../../skills/engineering/figma-arch-diagram/SKILL.md) and went out in sk-skills 2.2.0. Imported 2026-08-29 from the standalone `diagramming` repo it was written in, which was folded into this one and deleted. Paths and locations in the text below describe where the work happened at the time, not where the skill lives now.

**Date:** 2026-07-29
**Status:** Design approved, pending spec review

## Problem

Architecture and tech-stack diagrams built in Figma from the `Icon Lib - Editable` library come out messy often enough that the output has to be hand-repaired. Observed failure modes, taken from a real diagram (`PLANNED - CRM offline conversions close the loop`):

- A vertical connector dropped at a node's centre-x and struck through that node's own caption (`MKTG Site (Production)`).
- A branch elbow started mid-column instead of in the gap between columns, crossing both the `GA4 (G-SRHWP4RYKP)` label and the `online conversions` edge label.
- Captions ran two lines under one node and six under its neighbour, so the row had no shared baseline and the eye had nothing to track along.
- Two rows each read left-to-right but were chained head-to-tail, forcing the reader to jump backwards to follow the flow.

The reference for "clear" is the user's own `Data Tracking` board: stacked rows, each a strictly linear left-to-right chain, fan-outs occurring only after the last node of a chain, connectors confined to the gaps between columns, and colour-coded annotation cards in a fixed right-hand gutter.

The root cause is not one bug. It is that node placement and connector routing are done freehand at authoring time, against library components whose heights already disagree with each other.

## Current state of the library

`fileKey oGJ5pTR4dQI0EJhKDvdELz`, page `Components` (`0:1`), outer frame `Icon Nodes` (`292:209`).

The library has been rebuilt since the previously recorded notes and is now componentized. It contains 13 `Node/*` component sets keyed by a `Brand` variant, totalling ~117 brands:

| Component set | Node ID | Brands |
|---|---|---|
| `Node/Content & Marketing` | `307:318` | 7 |
| `Node/Security & CDN` | `307:372` | 4 |
| `Node/API & Services` | `308:543` | 5 |
| `Node/Business & Ops` | `333:165` | 2 |
| `Node/Language` | `307:580` | 17 |
| `Node/Framework` | `307:759` | 18 |
| `Node/DevOps` | `308:349` | 13 |
| `Node/Observability` | `308:458` | 9 |
| `Node/Messaging` | `308:571` | 2 |
| `Node/Data Store` | `310:383` | 11 |
| `Node/Server` | `315:319` | 5 |
| `Node/Client` | `308:605` | 3 |
| `Node/Adobe Experience Cloud` | `309:518` | 21 |

Plus untouched primitives copied from the original library: `Database` (`325:322`), `Service` (`325:335`), `ServiceHorizontal` (`325:348`), a second `Service` (`325:361`), `Queue` (`325:374`), `IconUserIcon` (`325:409`).

Two findings drive the design:

**Card heights are ragged at the source.** Components are 140 wide but 140, 160 (label wraps to two lines), 180.5 (cylinder data stores), or 192 (`Brand=Google Tag Manager`) tall. Any row mixing categories inherits ragged bottoms before the generator runs. This is a library defect, not a generator defect.

**The target card pattern already exists.** `Brand=Google Tag Manager` (`307:254`, 140×192) is already built as title-on-top / icon / instance-ID-on-bottom. Every other component still uses a single label underneath. The icon work is propagating one component's pattern to the other ~116, not inventing a pattern.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Where the fix lives | New personal skill developed in `~/Development/diagramming/skills/figma-arch-diagram/` and symlinked into `~/.claude/skills/`, delegating plugin-API mechanics to `figma-use` | The Figma plugin's skills live in `~/.claude/plugins/cache/claude-plugins-official/figma/<version>/` and are replaced on every plugin update: `2.2.78` and `2.2.81` are both already cached. Edits there would not survive. |
| Diagram shapes supported | Linear pipeline rows, nested grouping boxes, network/mesh topology, and vertical layered stacks | User requires all four; direction is a per-diagram parameter, not a fixed house style. |
| Long per-node prose | Inside the card, in a capped detail band | Text inside a solid card can never be struck through by a connector that stops at the card border. This is a structural guarantee, not a convention. |
| Detail-band overflow | Hard cap, spill to a Note component | Keeps rows compact and uniform; nothing is lost. |
| Note placement | Reserved note lane **above** the row, with a stub to its node | Gives the requested node adjacency while keeping the grid rigid, and preserves the space *below* a row, which is where every fan-out drop needs to go. |
| Iteration model | Spec stored in the frame's plugin data **and** as a sidecar `.yaml`; edits always trigger a full rebuild | Diagrams stay self-describing, specs stay diffable, and layout is globally re-solved every time so it cannot degrade across edits. Patch-in-place was rejected, since incremental insertion is roughly how the messy diagram became messy. |
| Ordering | Library normalization first, generator second | The card geometry is the layout engine's primary input. |

## Part 1: Library changes

### 1.1 Normalized card

Four fixed bands, top to bottom:

| Band | Contents | Height |
|---|---|---|
| ① Title | Brand or role name | Fixed, 2 lines at the title text style |
| ② Icon | Existing browser-chrome or cylinder artwork, vertically centred | Fixed, set by the tallest artwork in the library (the cylinder data stores) |
| ③ Instance | Instance identifier: account ID, environment, hostname | Fixed, 1 line |
| ④ Detail | Free prose, hard-capped at 4 lines, hidden by default | Fixed when shown, 0 when hidden |

Width stays 140. Exact band pixel values are derived in implementation by measuring `Brand=Google Tag Manager` (`307:254`) and the tallest cylinder in `Node/Data Store` (`310:383`); the rules are fixed here, the constants are measured, not guessed.

Consequences:

- Exactly **two card heights** exist across the whole library: `compact` (bands ①②③) and `extended` (①②③④), toggled by a boolean component property on band ④.
- Browser-chrome brands gain vertical padding so their icon band matches the cylinder's. This is the deliberate cost of a uniform grid.
- A shared row baseline becomes structural. The generator never computes or corrects it.

In the library palette each component ships with its brand name pre-filled in band ① and a representative sample value in band ③ (`GTM-123456`, `AW-XXXXXXXXX`, `G-XXXXXXXXXX`), so an instance is usable immediately and the expected format is self-documenting.

### 1.2 Note component

A new `Note` component set with a `Kind` variant: `warn` (yellow), `broken` (red), `ok` (green), matching the colour coding already used informally in the `Data Tracking` board's gutter cards. Anatomy: rounded card at card width, a coloured circular icon at the left, prose to the right.

Used in two places, same component: in the note lane above a row bound to a single node, and stacked in the right-hand gutter as phase-level annotations.

### 1.3 Migration

All ~117 brand components are restructured by script, not by hand. The `Brand` variant names and component-set node IDs are preserved so existing instances elsewhere keep resolving.

**Safety gate:** the normalization runs against a duplicate of the library file first. The rewritten library replaces the working file only after visual sign-off. Rewriting 117 live components in place is not reversible through the plugin API.

Existing diagrams already on canvas are not migrated. Their instances detach or keep their old geometry; they are left alone unless explicitly regenerated from a spec.

## Part 2: The `figma-arch-diagram` skill

### 2.1 Governing rule

**Nothing is ever placed by hand**, not by the assistant and not by a subagent. Diagrams are authored as a spec, coordinates are computed by a deterministic script, and Figma receives only already-solved numbers. Freehand placement is the cause of the original problem and the skill forbids it.

### 2.2 Stage 1: Spec

A declarative YAML describing the diagram: `direction` (`LR` or `TB`), rows with titles, nodes (brand, title, instance, optional detail), edges with labels, notes bound to nodes, branches, group boxes, and gutter annotations. This is the only artifact discussed when authoring or editing a diagram.

Written to the frame's plugin data and to a sidecar `.yaml`, kept in sync. Either is sufficient to rebuild.

### 2.3 Stage 2: Layout

`scripts/layout.mjs` is a pure function: spec in, absolute coordinates out, no Figma involvement. Unit-testable, and developed test-first against the user's real diagrams as fixtures.

Responsibilities:

- **Grid**: column pitch and row pitch derived from the two card heights fixed in Part 1.
- **Lane allocation**: every horizontal band and vertical gutter is a numbered track. Connectors may only occupy tracks. Cards and notes never do. This is the mechanism that makes text/connector collisions impossible rather than unlikely.
- **Orthogonal routing with channel assignment**: for the mesh case, edges are assigned to tracks and tracks are ordered to minimize crossings.
- **Group boxes**: padded bounding boxes that reserve a track around their perimeter so edges crossing a boundary have somewhere legal to run.
- **Direction**: `LR` and `TB` are an axis swap over identical code.

### 2.4 Stage 3: Emit

A single `use_figma` script that instantiates from the component sets, sets the `Brand` variant, fills the four text bands, toggles the detail band, and draws connectors as orthogonal polylines with arrow caps and background-filled label chips. It places at the coordinates stage 2 solved and makes no layout decisions of its own.

### 2.5 Stage 4: Verify

After building, the frame is read back and asserted against:

1. No text bounding box intersects any connector segment.
2. No two cards overlap.
3. Every card in a row shares `y` and height.
4. No connector enters a card or note rectangle.

On failure the offending lane is widened and the diagram re-emitted. A screenshot is then taken for a visual read. This stage is what converts "usually clean" into "clean", and it is not optional.

### 2.6 Skill layout

Developed in the `diagramming` repo and symlinked into `~/.claude/skills/figma-arch-diagram`, matching the existing pattern used for `find-skills`, `vercel-cli`, and `tanstack-start-best-practices`.

```
~/Development/diagramming/skills/figma-arch-diagram/
  SKILL.md                  # triggers, the four-stage workflow, the no-freehand rule
  scripts/
    layout.mjs              # spec -> coordinates (pure, tested)
    layout.test.mjs
  references/
    spec-format.md          # the YAML contract
    layout-engine.md        # grid, lanes, routing, constants
    library-map.md          # category -> component set node ID, brand inventory
    emit-recipes.md         # use_figma snippets: instance, variant swap, band text, polyline, group box
    verify.md               # the four assertions and the repair loop
```

`SKILL.md` directs the reader to `figma-use` for plugin-API mechanics rather than restating them.

## CORRECTION: diagrams are built in FigJam, not Figma Design

Recorded 2026-07-29, after Phase 1 shipped. **This spec was written on the wrong assumption and Phase 2 must be planned against this section, not the Design-file text below.**

The diagrams live on **FigJam boards** (`figma.com/board/...`), not Design files. This changes Phase 2 substantially, and mostly in our favour:

- **FigJam has a native connector primitive.** `figma.createConnector()` binds endpoints to nodes via `connectorStart` / `connectorEnd` with a `magnet` (`AUTO` / `TOP` / `BOTTOM` / `LEFT` / `RIGHT`), and connectors reroute themselves when nodes move. Most of the orthogonal-routing engine this spec called for is unnecessary; the effort moves to **placement, lane discipline, and explicit magnet choice**.
- **Explicit magnets are the fix for the original bug.** Binding a horizontal-flow edge with `RIGHT` → `LEFT` magnets attaches it at the card border. Because all text now lives *inside* a solid card, a border-attached connector cannot cross it. `AUTO` magnets must not be used for flow edges; that is what lets Figma route a line through a label.
- **Connectors carry their own label** (`connector.text.characters`), positioned by FigJam. This removes the hand-placed edge-label collisions seen in the original diagram.
- **Components are placed by key, not node id.** In a FigJam file the library components are foreign, so Phase 2 uses `figma.importComponentByKeyAsync(key)` then `.createInstance()`. All 121 keys are captured in `references/component-keys.json`. **This requires the library to be published**: node ids are useless across files.
- **No auto-layout in FigJam.** Card instances render as authored, but Phase 2 cannot rely on auto-layout for board-level composition; positions are computed and set explicitly.
- **FigJam-only API surface.** `figma.createPage()` is Design-only and throws in FigJam. Organize with FigJam sections instead.

Phase 2's verification pass still applies unchanged, including the `absoluteRenderBounds` lesson below.

## As built: Phase 1 outcome and deviations from this spec

Phase 1 shipped 2026-07-29 on branch `feat/library-normalization`. **Where this section disagrees with the text above or with the Phase 1 plan, this section is correct**: the reference files in `skills/figma-arch-diagram/references/` are the source of truth for Phase 2, not the plan's code samples.

Measured constants, locked after a rendered comparison of three candidate icon-band heights: `W` 140, `PAD` 18, `GAP` 12, `LINE_H` 20, `TITLE_H` 40 (2 lines), `ICON_H` 72, `ID_H` 20, `DETAIL_H` 80, `H_COMPACT` 192, `H_EXTENDED` 284. Text is Nunito SemiBold Italic at 15 / 13 / 11 for Title / Id / Detail. `H_COMPACT` 192 coincides exactly with the pre-existing `Google Tag Manager` exemplar.

Deviations, each deliberate:

- **Icons scale per brand** by `min(1, ICON_H / brand.icon.h)`, never by a shape-class constant. Six distinct factors occur in practice (Client 0.9231 / 0.96 / 0.8558, Server 0.6372, Data Store 0.64, Rust 0.9796). The `CHROME_SCALE` / `CYLINDER_SCALE` constants were written and then removed because they were unused and `0.6372` was wrong for Data Store's 112.5px cylinders.
- **Icon layer names are not uniform.** The five `Node/Server` brands use a layer named `Rack`; the other 112 use `icon`. Every brand's real layer name is recorded as `icon.iconLayerName` in `library-inventory.json`. Never hardcode `"icon"`.
- **The `Note` component hugs its content vertically** rather than using a fixed height. The spec's fixed-height note would clip long prose, which is the only reason the component exists.
- **`Customer Journey Analytics` carries the title `CJA`.** It is the only brand whose name cannot fit the two-line title band: "Customer Journey" measures 123px against a 104px box. Recorded as `v2TitleOverride` in the inventory so a regeneration cannot silently reintroduce the overflow.
- **Six sample IDs were shortened** (Sanity, Prismic, Meta Pixel, ClickUp, Akamai, Twilio) because the originals wrapped past the one-line Id band.

**Lesson that Phase 2's verification pass must inherit:** a wrapping text node in Figma keeps its declared dimensions: a `104x20` box still reports `104x20` when its text spills to two lines. Overflow is only detectable via `absoluteRenderBounds`. Every text-fit assertion in Phase 2's verifier must measure rendered ink, not node size.

Pages: `Components` (`352:113`) is live; `Components (legacy — pre-normalization)` (`0:1`) holds the untouched originals. Rollback is renaming the two pages back.

## Out of scope

- Migrating existing diagrams already drawn on canvas.
- `generate_diagram` / Mermaid / FigJam output: a different tool with different constraints, and not what produces these diagrams.
- Any edit to the vendored Figma plugin skills.
- Non-architecture diagram types (gantt, ERD, sequence).

## Risks

- **Library-map staleness.** `references/library-map.md` caches component-set node IDs. If the library is restructured again the map goes stale. Mitigated by verifying node IDs resolve at the start of each run and re-reading the library if they do not.
- **Uniform icon band adds height.** Browser-chrome brands become taller than they strictly need to be. Accepted deliberately in exchange for the shared baseline.
- **Rebuild discards hand-tweaks.** Any manual adjustment made in Figma is lost on the next regenerate. This is the accepted trade for layout that never degrades; the mitigation is that changes should be made to the spec.
- **Connector drawing in Design files.** Figma Design has no native connector primitive as FigJam does; polylines are drawn explicitly. Arrowhead and elbow-radius fidelity needs to be validated early against the existing diagrams' look.

## Open questions

- Which file(s) new diagrams are built into: resolved per invocation, the skill asks.
- Whether the sidecar spec directory should be version-controlled, and where it lives.
