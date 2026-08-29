# figma-arch-diagram Skill Implementation Plan

Status: implemented. Phase 2 of the design record in [`2026-07-29-figma-arch-diagram-design.md`](./2026-07-29-figma-arch-diagram-design.md). Imported 2026-08-29 from the standalone `diagramming` repo, which was folded into this one and deleted. The task checkboxes are left as they were worked.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `figma-arch-diagram` skill so architecture diagrams are authored as a declarative spec, placed by a deterministic tested engine, emitted to FigJam with native connectors, and verified before being called done.

**Architecture:** Four stages. A YAML-ish spec object describes the diagram. `scripts/layout.mjs` is a pure function (spec in, absolute coordinates out) with no Figma involvement, so it is unit-testable with `node --test`. A FigJam emitter places library components by key and draws native connectors with explicit magnets. A verification pass reads the board back and asserts no text is clipped and no card overlaps, using `absoluteRenderBounds` rather than node dimensions.

**Tech Stack:** Node v24 (`node --test`, `node:assert/strict`), ES modules; Figma Plugin API via the `figma-personal` MCP server (`use_figma`, `get_screenshot`) against FigJam boards.

## Global Constraints

- **Target surface is FigJam** (`figma.com/board/...`), never Figma Design. `figma.createPage()` is Design-only and throws in FigJam, so organize with FigJam sections instead.
- **Read the `figma-use` skill before every `use_figma` call**, and `figma-use-figjam` for FigJam specifics. Neither is an invocable Skill in this environment, so read from disk: `/Users/samkumar/.claude/plugins/cache/claude-plugins-official/figma/2.2.81/skills/figma-use/SKILL.md` and `.../figma-use-figjam/SKILL.md`, references in their sibling `references/` directories.
- **Never use the sync `figma.currentPage =` setter**: it throws. Use `await figma.setCurrentPageAsync(page)`.
- **Cards are placed by component KEY, not node id.** `figma.importComponentByKeyAsync(key)` then `.createInstance()`. All 121 keys are in `skills/figma-arch-diagram/references/component-keys.json`. Requires the `Icon Lib - Editable` library to be published.
- **Card geometry is fixed:** width 140, height 192 compact / 284 extended. Read from `skills/figma-arch-diagram/references/card-constants.json`; never retype.
- **Flow edges must use explicit magnets**: `RIGHT`→`LEFT` for `LR`, `BOTTOM`→`TOP` for `TB` and for branch drops. **`AUTO` is forbidden on flow edges**: it is what lets Figma route a line through a label, which is the original bug this skill exists to prevent.
- **A new connector's `text.fontName` is invalid by default.** Calling `figma.loadFontAsync(connector.text.fontName)` throws. Load a known font, assign `connector.text.fontName` explicitly, then set `connector.text.characters`. Setting `connector.name` does nothing visible.
- **`appendChild` to a section makes coordinates section-local.** Always append first, then set `x`/`y`. After adding children, resize the section to encompass them.
- **Text overflow is only detectable via `absoluteRenderBounds`.** A 104x20 text node still reports 104x20 when its text wraps to two lines. Every text-fit assertion must measure rendered ink.
- Repo `/Users/samkumar/Development/diagramming`. Commits must contain no Co-Authored-By trailer, no "Generated with Claude Code" footer, no emoji, and no mention of Claude/Anthropic/AI.
- Markdown in this repo must not be hard-wrapped at a fixed column: one line per paragraph and per list item.

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/figma-arch-diagram/SKILL.md` | Trigger conditions, the four-stage workflow, the no-freehand rule. Delegates plugin-API mechanics to `figma-use` / `figma-use-figjam`. |
| `skills/figma-arch-diagram/scripts/spec.mjs` | Spec normalization and validation. Pure. |
| `skills/figma-arch-diagram/scripts/spec.test.mjs` | Tests for the above. |
| `skills/figma-arch-diagram/scripts/layout.mjs` | Spec → absolute coordinates. Pure, no Figma. The engine. |
| `skills/figma-arch-diagram/scripts/layout.test.mjs` | Tests for the above. |
| `skills/figma-arch-diagram/references/spec-format.md` | The authoring contract: what a diagram spec looks like. |
| `skills/figma-arch-diagram/references/emit-recipes.md` | `use_figma` snippets: import by key, set band text, connectors, sections. |
| `skills/figma-arch-diagram/references/verify.md` | The assertions and the repair loop. |
| `skills/figma-arch-diagram/references/*.json`, `library-map.md` | Existing Phase 1 data. Not modified. |

---

### Task 1: Spec normalization and validation

The authoring contract. Everything downstream consumes a *normalized* spec, so defaults are applied exactly once, here.

**Files:**
- Create: `skills/figma-arch-diagram/scripts/spec.mjs`
- Create: `skills/figma-arch-diagram/scripts/spec.test.mjs`
- Create: `skills/figma-arch-diagram/references/spec-format.md`

**Interfaces:**
- Produces: `normalizeSpec(raw)` → normalized spec object, and throws `Error` with a specific message on invalid input. Later tasks call `normalizeSpec` then pass its result to `layout`.

Normalized shape, with every field present and defaults applied:

```js
{
  title: string,
  direction: "LR" | "TB",          // default "LR"
  rows: [{
    id: string,
    title: string,                  // "" if absent
    nodes: [{
      id: string, category: string, brand: string,
      title: string, instance: string,
      detail: string,               // "" if absent
      lane: "main" | "sub"          // default "main"
    }],
    edges: [{ from: string, to: string, label: string }],
    notes: [{ on: string, kind: "warn"|"broken"|"ok", text: string }]
  }],
  edges: [{ from: string, to: string, label: string }],   // CROSS-ROW edges, top level
  annotations: [{ kind: "warn"|"broken"|"ok", title: string, text: string }]
}
```

**Row edges vs cross-row edges.** `row.edges` connect nodes within one row. Top-level `spec.edges` connect nodes in *different* rows; the original messy diagram had exactly this (a site in the top row feeding a call-tracking node in the bottom row), and without it that relationship cannot be expressed at all. Both are validated against the same global node-id set.

- [ ] **Step 1: Write the failing tests**

```js
// skills/figma-arch-diagram/scripts/spec.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { normalizeSpec } from './spec.mjs'

const minimal = {
  title: 'T',
  rows: [{ id: 'r1', nodes: [{ id: 'a', category: 'Node/Framework', brand: 'Next.js', title: 'Site', instance: 'prod' }] }]
}

test('applies defaults', () => {
  const s = normalizeSpec(minimal)
  assert.equal(s.direction, 'LR')
  assert.equal(s.rows[0].title, '')
  assert.equal(s.rows[0].nodes[0].lane, 'main')
  assert.equal(s.rows[0].nodes[0].detail, '')
  assert.deepEqual(s.rows[0].edges, [])
  assert.deepEqual(s.rows[0].notes, [])
  assert.deepEqual(s.annotations, [])
})

test('does not mutate the input', () => {
  const raw = JSON.parse(JSON.stringify(minimal))
  normalizeSpec(raw)
  assert.deepEqual(raw, minimal)
})

test('rejects an unknown direction', () => {
  assert.throws(() => normalizeSpec({ ...minimal, direction: 'DIAGONAL' }), /direction must be LR or TB/)
})

test('rejects duplicate node ids across rows', () => {
  const dup = { title: 'T', rows: [
    { id: 'r1', nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }] },
    { id: 'r2', nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }] }
  ] }
  assert.throws(() => normalizeSpec(dup), /duplicate node id: a/)
})

test('rejects an edge referencing an unknown node', () => {
  const bad = { title: 'T', rows: [{ id: 'r1',
    nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }],
    edges: [{ from: 'a', to: 'ghost' }] }] }
  assert.throws(() => normalizeSpec(bad), /edge target not found: ghost/)
})

test('rejects a note attached to an unknown node', () => {
  const bad = { title: 'T', rows: [{ id: 'r1',
    nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }],
    notes: [{ on: 'ghost', kind: 'warn', text: 'x' }] }] }
  assert.throws(() => normalizeSpec(bad), /note target not found: ghost/)
})

test('rejects an unknown note kind', () => {
  const bad = { title: 'T', rows: [{ id: 'r1',
    nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }],
    notes: [{ on: 'a', kind: 'info', text: 'x' }] }] }
  assert.throws(() => normalizeSpec(bad), /note kind must be warn, broken or ok/)
})

test('accepts cross-row edges at the top level', () => {
  const s = normalizeSpec({ title: 'T',
    rows: [
      { id: 'r1', nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }] },
      { id: 'r2', nodes: [{ id: 'z', category: 'c', brand: 'b', title: 't', instance: 'i' }] }
    ],
    edges: [{ from: 'a', to: 'z', label: 'form submit' }] })
  assert.equal(s.edges.length, 1)
  assert.equal(s.edges[0].label, 'form submit')
})

test('rejects a cross-row edge referencing an unknown node', () => {
  const bad = { title: 'T',
    rows: [{ id: 'r1', nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i' }] }],
    edges: [{ from: 'a', to: 'ghost' }] }
  assert.throws(() => normalizeSpec(bad), /edge target not found: ghost/)
})

test('rejects detail longer than 4 lines', () => {
  const bad = { title: 'T', rows: [{ id: 'r1',
    nodes: [{ id: 'a', category: 'c', brand: 'b', title: 't', instance: 'i', detail: 'a\nb\nc\nd\ne' }] }] }
  assert.throws(() => normalizeSpec(bad), /detail exceeds 4 lines/)
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test spec.test.mjs`
Expected: FAIL, `Cannot find module './spec.mjs'`.

- [ ] **Step 3: Implement**

```js
// skills/figma-arch-diagram/scripts/spec.mjs
const KINDS = new Set(['warn', 'broken', 'ok'])

export function normalizeSpec (raw) {
  if (!raw || typeof raw !== 'object') throw new Error('spec must be an object')
  if (!raw.title) throw new Error('spec.title is required')

  const direction = raw.direction ?? 'LR'
  if (direction !== 'LR' && direction !== 'TB') throw new Error('direction must be LR or TB')

  const seen = new Set()
  const rows = (raw.rows ?? []).map(row => {
    if (!row.id) throw new Error('every row needs an id')
    const nodes = (row.nodes ?? []).map(n => {
      for (const f of ['id', 'category', 'brand', 'title', 'instance']) {
        if (!n[f]) throw new Error(`node.${f} is required (node ${n.id ?? '?'})`)
      }
      if (seen.has(n.id)) throw new Error(`duplicate node id: ${n.id}`)
      seen.add(n.id)
      const detail = n.detail ?? ''
      if (detail.split('\n').length > 4) throw new Error(`detail exceeds 4 lines (node ${n.id})`)
      const lane = n.lane ?? 'main'
      if (lane !== 'main' && lane !== 'sub') throw new Error(`lane must be main or sub (node ${n.id})`)
      return { id: n.id, category: n.category, brand: n.brand, title: n.title, instance: n.instance, detail, lane }
    })
    return {
      id: row.id,
      title: row.title ?? '',
      nodes,
      edges: (row.edges ?? []).map(e => ({ from: e.from, to: e.to, label: e.label ?? '' })),
      notes: (row.notes ?? []).map(n => {
        if (!KINDS.has(n.kind)) throw new Error('note kind must be warn, broken or ok')
        return { on: n.on, kind: n.kind, text: n.text ?? '' }
      })
    }
  })

  for (const row of rows) {
    for (const e of row.edges) {
      if (!seen.has(e.from)) throw new Error(`edge source not found: ${e.from}`)
      if (!seen.has(e.to)) throw new Error(`edge target not found: ${e.to}`)
    }
    for (const n of row.notes) {
      if (!seen.has(n.on)) throw new Error(`note target not found: ${n.on}`)
    }
  }

  const edges = (raw.edges ?? []).map(e => {
    if (!seen.has(e.from)) throw new Error(`edge source not found: ${e.from}`)
    if (!seen.has(e.to)) throw new Error(`edge target not found: ${e.to}`)
    return { from: e.from, to: e.to, label: e.label ?? '' }
  })

  const annotations = (raw.annotations ?? []).map(a => {
    if (!KINDS.has(a.kind)) throw new Error('annotation kind must be warn, broken or ok')
    return { kind: a.kind, title: a.title ?? '', text: a.text ?? '' }
  })

  return { title: raw.title, direction, rows, edges, annotations }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test spec.test.mjs`
Expected: PASS, 10 tests.

- [ ] **Step 5: Write `references/spec-format.md`**

Document the normalized shape above, each field's meaning, the defaults, and every validation error the module can throw. Include one complete worked example, the user's real `SHIPPED: Production since v4.21.10` row: `MKTG Site` (Node/Framework, Next.js, instance `Production`) → `window.dataLayer` (Node/Language, JavaScript, instance `ad_phone_click`) → `Google Tag Manager` (Node/Content & Marketing, instance `GTM-5KJTHP3M`) → `Google tag` (instance `AW-794559089`) → `GA4` (instance `G-SRHWP4RYKP`), with `Google Ads` as a `lane: sub` node fed from `Google tag`, a `warn` note on the GTM node reading `NO phone numbers in container`, and an `ok` annotation.

- [ ] **Step 6: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/scripts/spec.mjs skills/figma-arch-diagram/scripts/spec.test.mjs skills/figma-arch-diagram/references/spec-format.md
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add diagram spec normalization and validation"
```

---

### Task 2: Layout engine: rows, cards, and flow edges

The core placement pass for `direction: LR`, main lane only. Notes, sub-lanes, annotations, and `TB` come in Tasks 3 and 4.

**Files:**
- Create: `skills/figma-arch-diagram/scripts/layout.mjs`
- Create: `skills/figma-arch-diagram/scripts/layout.test.mjs`

**Interfaces:**
- Consumes: `normalizeSpec(raw)` from Task 1.
- Produces: `layout(spec, constants)` → placement object; and the exported constant object `LAYOUT` with the spacing values below.

```js
{
  canvas: { width, height },
  sections: [{ id, title, x, y, width, height }],
  cards: [{ id, category, brand, title, instance, detail, showDetail, x, y, width, height }],
  notes: [],          // Task 3
  edges: [{ from, to, label, startMagnet, endMagnet }],
  annotations: []     // Task 3
}
```

`constants` is the parsed `card-constants.json`. Layout spacing lives in `LAYOUT`:

```js
export const LAYOUT = {
  COL_GAP: 80,       // horizontal space between cards; connector + label live here
  ROW_GAP: 140,      // vertical space between rows
  NOTE_BAND: 96,     // reserved height above a row when it has notes
  NOTE_GAP: 16,      // between a note and its card
  SUBROW_GAP: 90,    // between the main card row and a sub-lane row
  GUTTER_GAP: 120,   // between the widest row and the annotation gutter
  GUTTER_W: 260,
  SECTION_PAD: 40,
  ROW_TITLE_H: 44,
  MARGIN: 60
}
```

- [ ] **Step 1: Write the failing tests**

```js
// skills/figma-arch-diagram/scripts/layout.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { normalizeSpec } from './spec.mjs'
import { layout, LAYOUT } from './layout.mjs'

const C = JSON.parse(readFileSync(new URL('../references/card-constants.json', import.meta.url)))

function node (id, extra = {}) {
  return { id, category: 'Node/Framework', brand: 'Next.js', title: id, instance: 'v1', ...extra }
}

const threeInARow = normalizeSpec({
  title: 'T',
  rows: [{ id: 'r1', title: 'Row one', nodes: [node('a'), node('b'), node('c')],
           edges: [{ from: 'a', to: 'b', label: 'x' }, { from: 'b', to: 'c' }] }]
})

test('cards in a row share a y and a height', () => {
  const out = layout(threeInARow, C)
  const ys = new Set(out.cards.map(c => c.y))
  const hs = new Set(out.cards.map(c => c.height))
  assert.equal(ys.size, 1)
  assert.deepEqual([...hs], [C.H_COMPACT])
})

test('column pitch is card width plus the gap', () => {
  const out = layout(threeInARow, C)
  const xs = out.cards.map(c => c.x).sort((p, q) => p - q)
  assert.equal(xs[1] - xs[0], C.W + LAYOUT.COL_GAP)
  assert.equal(xs[2] - xs[1], C.W + LAYOUT.COL_GAP)
})

test('no two cards overlap', () => {
  const out = layout(threeInARow, C)
  for (let i = 0; i < out.cards.length; i++) {
    for (let j = i + 1; j < out.cards.length; j++) {
      const a = out.cards[i], b = out.cards[j]
      const disjoint = a.x + a.width <= b.x || b.x + b.width <= a.x ||
                       a.y + a.height <= b.y || b.y + b.height <= a.y
      assert.ok(disjoint, `${a.id} overlaps ${b.id}`)
    }
  }
})

test('LR flow edges use RIGHT to LEFT magnets, never AUTO', () => {
  const out = layout(threeInARow, C)
  assert.equal(out.edges.length, 2)
  for (const e of out.edges) {
    assert.equal(e.startMagnet, 'RIGHT')
    assert.equal(e.endMagnet, 'LEFT')
    assert.notEqual(e.startMagnet, 'AUTO')
  }
})

test('edge labels are carried through', () => {
  const out = layout(threeInARow, C)
  assert.equal(out.edges.find(e => e.from === 'a').label, 'x')
  assert.equal(out.edges.find(e => e.from === 'b').label, '')
})

test('a node with detail text gets the extended height', () => {
  const s = normalizeSpec({ title: 'T', rows: [{ id: 'r1', nodes: [node('a', { detail: 'one\ntwo' }), node('b')] }] })
  const out = layout(s, C)
  assert.equal(out.cards.find(c => c.id === 'a').showDetail, true)
  assert.equal(out.cards.find(c => c.id === 'b').showDetail, false)
  const hs = new Set(out.cards.map(c => c.height))
  assert.deepEqual([...hs], [C.H_EXTENDED], 'a row equalizes to the tallest card')
})

test('two rows are stacked and do not overlap vertically', () => {
  const s = normalizeSpec({ title: 'T', rows: [
    { id: 'r1', nodes: [node('a')] },
    { id: 'r2', nodes: [node('b')] }
  ] })
  const out = layout(s, C)
  const a = out.cards.find(c => c.id === 'a')
  const b = out.cards.find(c => c.id === 'b')
  assert.ok(b.y >= a.y + a.height + LAYOUT.ROW_GAP - 1, 'row 2 sits below row 1')
})

test('a row title produces a section that encloses its cards', () => {
  const out = layout(threeInARow, C)
  const sec = out.sections.find(s => s.id === 'r1')
  assert.ok(sec, 'section exists')
  for (const c of out.cards) {
    assert.ok(c.x >= sec.x && c.x + c.width <= sec.x + sec.width, 'card inside section horizontally')
    assert.ok(c.y >= sec.y && c.y + c.height <= sec.y + sec.height, 'card inside section vertically')
  }
})

test('layout is deterministic', () => {
  assert.deepEqual(layout(threeInARow, C), layout(threeInARow, C))
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test layout.test.mjs`
Expected: FAIL, `Cannot find module './layout.mjs'`.

- [ ] **Step 3: Implement**

```js
// skills/figma-arch-diagram/scripts/layout.mjs
export const LAYOUT = {
  COL_GAP: 80,
  ROW_GAP: 140,
  NOTE_BAND: 96,
  NOTE_GAP: 16,
  SUBROW_GAP: 90,
  GUTTER_GAP: 120,
  GUTTER_W: 260,
  SECTION_PAD: 40,
  ROW_TITLE_H: 44,
  MARGIN: 60
}

export function layout (spec, C) {
  const cards = []
  const edges = []
  const sections = []

  let cursorY = LAYOUT.MARGIN
  let widest = 0

  for (const row of spec.rows) {
    const main = row.nodes.filter(n => n.lane === 'main')
    const rowHasDetail = row.nodes.some(n => n.detail !== '')
    const cardH = rowHasDetail ? C.H_EXTENDED : C.H_COMPACT

    const sectionTop = cursorY
    const cardsY = sectionTop + LAYOUT.ROW_TITLE_H

    main.forEach((n, i) => {
      cards.push({
        id: n.id, category: n.category, brand: n.brand,
        title: n.title, instance: n.instance, detail: n.detail,
        showDetail: n.detail !== '',
        x: LAYOUT.MARGIN + i * (C.W + LAYOUT.COL_GAP),
        y: cardsY,
        width: C.W, height: cardH
      })
    })

    for (const e of row.edges) {
      edges.push({ from: e.from, to: e.to, label: e.label, startMagnet: 'RIGHT', endMagnet: 'LEFT' })
    }

    const rowRight = LAYOUT.MARGIN + Math.max(0, main.length - 1) * (C.W + LAYOUT.COL_GAP) + C.W
    widest = Math.max(widest, rowRight)

    const sectionBottom = cardsY + cardH
    sections.push({
      id: row.id, title: row.title,
      x: LAYOUT.MARGIN - LAYOUT.SECTION_PAD,
      y: sectionTop - LAYOUT.SECTION_PAD,
      width: (rowRight - LAYOUT.MARGIN) + LAYOUT.SECTION_PAD * 2,
      height: (sectionBottom - sectionTop) + LAYOUT.SECTION_PAD * 2
    })

    cursorY = sectionBottom + LAYOUT.ROW_GAP
  }

  return {
    canvas: { width: widest + LAYOUT.MARGIN, height: cursorY },
    sections, cards, notes: [], edges, annotations: []
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test layout.test.mjs`
Expected: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/scripts/layout.mjs skills/figma-arch-diagram/scripts/layout.test.mjs
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add layout engine for rows, cards and flow edges"
```

---

### Task 3: Layout: note lane, sub-lane rows, and the annotation gutter

The three placements that keep connectors and text apart. Notes go in a reserved band **above** each row so the space below stays free for sub-lane drops.

**Files:**
- Modify: `skills/figma-arch-diagram/scripts/layout.mjs`
- Modify: `skills/figma-arch-diagram/scripts/layout.test.mjs`

**Interfaces:**
- Consumes: `layout(spec, C)` and `LAYOUT` from Task 2.
- Produces: `out.notes` entries `{ id, on, kind, text, x, y, width }` where `id` is `note-<on>`; `out.annotations` entries `{ kind, title, text, x, y, width }`; and edges into `lane: "sub"` nodes carrying `startMagnet: 'BOTTOM'`, `endMagnet: 'TOP'`.

- [ ] **Step 1: Write the failing tests**

Append to `layout.test.mjs`:

```js
test('a note sits above its card, column-aligned, and clear of it', () => {
  const s = normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('a'), node('b')],
    notes: [{ on: 'b', kind: 'warn', text: 'careful' }] }] })
  const out = layout(s, C)
  const b = out.cards.find(c => c.id === 'b')
  const nte = out.notes.find(n => n.on === 'b')
  assert.ok(nte, 'note placed')
  assert.equal(nte.x, b.x, 'column-aligned with its card')
  assert.equal(nte.width, C.W)
  assert.ok(nte.y + LAYOUT.NOTE_BAND <= b.y, 'note band clears the card')
  assert.equal(nte.id, 'note-b')
})

test('a row without notes reserves no note band', () => {
  const withNote = layout(normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('a')], notes: [{ on: 'a', kind: 'ok', text: 'x' }] }] }), C)
  const without = layout(normalizeSpec({ title: 'T', rows: [{ id: 'r1', nodes: [node('a')] }] }), C)
  assert.ok(withNote.cards[0].y > without.cards[0].y, 'note band pushes the card down')
  assert.equal(withNote.cards[0].y - without.cards[0].y, LAYOUT.NOTE_BAND + LAYOUT.NOTE_GAP)
})

test('a sub-lane node drops below the row, aligned to its source column', () => {
  const s = normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('a'), node('b'), node('ads', { lane: 'sub' })],
    edges: [{ from: 'a', to: 'b' }, { from: 'b', to: 'ads' }] }] })
  const out = layout(s, C)
  const b = out.cards.find(c => c.id === 'b')
  const ads = out.cards.find(c => c.id === 'ads')
  assert.equal(ads.x, b.x, 'aligned under its source')
  assert.ok(ads.y >= b.y + b.height + LAYOUT.SUBROW_GAP - 1, 'drops below the main row')
})

test('an edge into a sub-lane node uses BOTTOM to TOP magnets', () => {
  const s = normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('b'), node('ads', { lane: 'sub' })],
    edges: [{ from: 'b', to: 'ads' }] }] })
  const out = layout(s, C)
  const e = out.edges[0]
  assert.equal(e.startMagnet, 'BOTTOM')
  assert.equal(e.endMagnet, 'TOP')
})

test('a sub-lane card is inside its row section', () => {
  const s = normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('b'), node('ads', { lane: 'sub' })],
    edges: [{ from: 'b', to: 'ads' }] }] })
  const out = layout(s, C)
  const sec = out.sections[0]
  const ads = out.cards.find(c => c.id === 'ads')
  assert.ok(ads.y + ads.height <= sec.y + sec.height, 'section encloses the sub row')
})

test('annotations stack in a gutter right of the widest row', () => {
  const s = normalizeSpec({ title: 'T',
    rows: [{ id: 'r1', nodes: [node('a'), node('b'), node('c')] }],
    annotations: [{ kind: 'ok', title: 'A', text: 'first' }, { kind: 'warn', title: 'B', text: 'second' }] })
  const out = layout(s, C)
  assert.equal(out.annotations.length, 2)
  const rightmost = Math.max(...out.cards.map(c => c.x + c.width))
  for (const a of out.annotations) {
    assert.ok(a.x >= rightmost + LAYOUT.GUTTER_GAP, 'gutter is clear of every card')
    assert.equal(a.width, LAYOUT.GUTTER_W)
  }
  assert.ok(out.annotations[1].y > out.annotations[0].y, 'annotations stack downward')
})

test('a cross-row edge is emitted with BOTTOM to TOP magnets', () => {
  const s = normalizeSpec({ title: 'T',
    rows: [
      { id: 'r1', nodes: [node('a')] },
      { id: 'r2', nodes: [node('z')] }
    ],
    edges: [{ from: 'a', to: 'z', label: 'form submit' }] })
  const out = layout(s, C)
  const cross = out.edges.find(e => e.from === 'a' && e.to === 'z')
  assert.ok(cross, 'cross-row edge is placed')
  assert.equal(cross.startMagnet, 'BOTTOM')
  assert.equal(cross.endMagnet, 'TOP')
  assert.equal(cross.label, 'form submit')
})

test('nothing in the gutter overlaps any card', () => {
  const s = normalizeSpec({ title: 'T',
    rows: [{ id: 'r1', nodes: [node('a')] }],
    annotations: [{ kind: 'ok', title: 'A', text: 'x' }] })
  const out = layout(s, C)
  for (const a of out.annotations) {
    for (const c of out.cards) {
      assert.ok(a.x >= c.x + c.width, `annotation overlaps card ${c.id}`)
    }
  }
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test layout.test.mjs`
Expected: FAIL, the 8 new tests fail (`out.notes` is empty, sub-lane cards are not placed, `out.annotations` is empty). The 9 tests from Task 2 must still PASS.

- [ ] **Step 3: Implement**

Replace the body of the `for (const row of spec.rows)` loop and the return in `layout.mjs`:

```js
  for (const row of spec.rows) {
    const main = row.nodes.filter(n => n.lane === 'main')
    const subs = row.nodes.filter(n => n.lane === 'sub')
    const rowHasDetail = row.nodes.some(n => n.detail !== '')
    const cardH = rowHasDetail ? C.H_EXTENDED : C.H_COMPACT
    const hasNotes = row.notes.length > 0

    const sectionTop = cursorY
    const noteY = sectionTop + LAYOUT.ROW_TITLE_H
    const cardsY = hasNotes ? noteY + LAYOUT.NOTE_BAND + LAYOUT.NOTE_GAP : noteY

    const colX = {}
    main.forEach((n, i) => {
      const x = LAYOUT.MARGIN + i * (C.W + LAYOUT.COL_GAP)
      colX[n.id] = x
      cards.push({
        id: n.id, category: n.category, brand: n.brand,
        title: n.title, instance: n.instance, detail: n.detail,
        showDetail: n.detail !== '',
        x, y: cardsY, width: C.W, height: cardH
      })
    })

    for (const n of row.notes) {
      notes.push({ id: `note-${n.on}`, on: n.on, kind: n.kind, text: n.text,
                   x: colX[n.on], y: noteY, width: C.W })
    }

    const subY = cardsY + cardH + LAYOUT.SUBROW_GAP
    subs.forEach((n, i) => {
      const feeder = row.edges.find(e => e.to === n.id)
      const x = (feeder && colX[feeder.from] !== undefined)
        ? colX[feeder.from]
        : LAYOUT.MARGIN + i * (C.W + LAYOUT.COL_GAP)
      colX[n.id] = x
      cards.push({
        id: n.id, category: n.category, brand: n.brand,
        title: n.title, instance: n.instance, detail: n.detail,
        showDetail: n.detail !== '',
        x, y: subY, width: C.W, height: cardH
      })
    })

    const subIds = new Set(subs.map(n => n.id))
    for (const e of row.edges) {
      const down = subIds.has(e.to)
      edges.push({
        from: e.from, to: e.to, label: e.label,
        startMagnet: down ? 'BOTTOM' : 'RIGHT',
        endMagnet: down ? 'TOP' : 'LEFT'
      })
    }

    const rowRight = LAYOUT.MARGIN + Math.max(0, main.length - 1) * (C.W + LAYOUT.COL_GAP) + C.W
    widest = Math.max(widest, rowRight)

    const sectionBottom = (subs.length ? subY + cardH : cardsY + cardH)
    sections.push({
      id: row.id, title: row.title,
      x: LAYOUT.MARGIN - LAYOUT.SECTION_PAD,
      y: sectionTop - LAYOUT.SECTION_PAD,
      width: (rowRight - LAYOUT.MARGIN) + LAYOUT.SECTION_PAD * 2,
      height: (sectionBottom - sectionTop) + LAYOUT.SECTION_PAD * 2
    })

    cursorY = sectionBottom + LAYOUT.ROW_GAP
  }

  // Cross-row edges: always a vertical hop between rows, so BOTTOM -> TOP in LR,
  // and RIGHT -> LEFT in TB where rows stack the other way.
  // Rows stack vertically in BOTH directions, so a cross-row edge is always a vertical hop.
  for (const e of spec.edges) {
    edges.push({ from: e.from, to: e.to, label: e.label, startMagnet: 'BOTTOM', endMagnet: 'TOP' })
  }

  const gutterX = widest + LAYOUT.GUTTER_GAP
  let gy = LAYOUT.MARGIN
  for (const a of spec.annotations) {
    annotations.push({ kind: a.kind, title: a.title, text: a.text, x: gutterX, y: gy, width: LAYOUT.GUTTER_W })
    gy += 180
  }

  return {
    canvas: { width: gutterX + LAYOUT.GUTTER_W + LAYOUT.MARGIN, height: Math.max(cursorY, gy) },
    sections, cards, notes, edges, annotations
  }
```

Declare `const notes = []` and `const annotations = []` alongside `cards`, `edges`, and `sections` at the top of `layout`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test`
Expected: PASS, 27 tests across both files.

- [ ] **Step 5: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/scripts/layout.mjs skills/figma-arch-diagram/scripts/layout.test.mjs
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add note lane, sub-lane rows and annotation gutter to layout"
```

---

### Task 4: Layout: top-to-bottom direction

`TB` is an axis swap over the same placement logic: columns become rows, and flow magnets become `BOTTOM`→`TOP`.

**Files:**
- Modify: `skills/figma-arch-diagram/scripts/layout.mjs`
- Modify: `skills/figma-arch-diagram/scripts/layout.test.mjs`

**Interfaces:**
- Consumes: `layout(spec, C)` from Task 3.
- Produces: no new exports. `spec.direction === 'TB'` changes card positions and flow magnets only; the returned object keeps the same shape.

- [ ] **Step 1: Write the failing tests**

Append to `layout.test.mjs`:

```js
const tbSpec = normalizeSpec({
  title: 'T', direction: 'TB',
  rows: [{ id: 'r1', nodes: [node('a'), node('b'), node('c')],
           edges: [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }] }]
})

test('TB stacks cards vertically in one column', () => {
  const out = layout(tbSpec, C)
  const xs = new Set(out.cards.map(c => c.x))
  assert.equal(xs.size, 1, 'all cards share a column')
  const ys = out.cards.map(c => c.y).sort((p, q) => p - q)
  assert.equal(ys[1] - ys[0], C.H_COMPACT + LAYOUT.COL_GAP)
})

test('TB flow edges use BOTTOM to TOP magnets', () => {
  const out = layout(tbSpec, C)
  for (const e of out.edges) {
    assert.equal(e.startMagnet, 'BOTTOM')
    assert.equal(e.endMagnet, 'TOP')
  }
})

test('TB cards do not overlap', () => {
  const out = layout(tbSpec, C)
  for (let i = 0; i < out.cards.length; i++) {
    for (let j = i + 1; j < out.cards.length; j++) {
      const a = out.cards[i], b = out.cards[j]
      const disjoint = a.x + a.width <= b.x || b.x + b.width <= a.x ||
                       a.y + a.height <= b.y || b.y + b.height <= a.y
      assert.ok(disjoint, `${a.id} overlaps ${b.id}`)
    }
  }
})

test('TB sub-lane nodes go to the right, using RIGHT to LEFT', () => {
  const s = normalizeSpec({ title: 'T', direction: 'TB', rows: [{ id: 'r1',
    nodes: [node('b'), node('side', { lane: 'sub' })],
    edges: [{ from: 'b', to: 'side' }] }] })
  const out = layout(s, C)
  const b = out.cards.find(c => c.id === 'b')
  const side = out.cards.find(c => c.id === 'side')
  assert.ok(side.x > b.x + b.width, 'sub node sits to the right')
  assert.equal(side.y, b.y, 'aligned on its source row')
  assert.equal(out.edges[0].startMagnet, 'RIGHT')
  assert.equal(out.edges[0].endMagnet, 'LEFT')
})

test('LR output is unchanged by the TB code path', () => {
  const before = layout(threeInARow, C)
  layout(tbSpec, C)
  assert.deepEqual(layout(threeInARow, C), before)
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test layout.test.mjs`
Expected: FAIL, the 5 new TB tests fail; all 27 earlier tests still PASS.

- [ ] **Step 3: Implement**

In `layout.mjs`, introduce a direction-aware placement helper and use it for both main and sub cards. Replace the `main.forEach` and `subs.forEach` blocks:

```js
    const vertical = spec.direction === 'TB'

    const colX = {}
    const colY = {}
    main.forEach((n, i) => {
      const x = vertical ? LAYOUT.MARGIN : LAYOUT.MARGIN + i * (C.W + LAYOUT.COL_GAP)
      const y = vertical ? cardsY + i * (cardH + LAYOUT.COL_GAP) : cardsY
      colX[n.id] = x
      colY[n.id] = y
      cards.push({
        id: n.id, category: n.category, brand: n.brand,
        title: n.title, instance: n.instance, detail: n.detail,
        showDetail: n.detail !== '',
        x, y, width: C.W, height: cardH
      })
    })

    for (const n of row.notes) {
      // TB: sub-lane nodes occupy the right, so the note band goes LEFT of the column.
      // Placing a TB note at its card's own x/y puts it exactly on top of the card.
      notes.push({ id: `note-${n.on}`, on: n.on, kind: n.kind, text: n.text,
                   x: vertical ? LAYOUT.MARGIN : colX[n.on],
                   y: vertical ? colY[n.on] : noteY, width: C.W })
    }

    subs.forEach((n, i) => {
      const feeder = row.edges.find(e => e.to === n.id)
      const src = feeder ? feeder.from : null
      const x = vertical
        ? (src !== null ? colX[src] + C.W + LAYOUT.SUBROW_GAP : LAYOUT.MARGIN + C.W + LAYOUT.SUBROW_GAP)
        : (src !== null ? colX[src] : LAYOUT.MARGIN + i * (C.W + LAYOUT.COL_GAP))
      const y = vertical
        ? (src !== null ? colY[src] : cardsY + i * (cardH + LAYOUT.COL_GAP))
        : cardsY + cardH + LAYOUT.SUBROW_GAP
      colX[n.id] = x
      colY[n.id] = y
      cards.push({
        id: n.id, category: n.category, brand: n.brand,
        title: n.title, instance: n.instance, detail: n.detail,
        showDetail: n.detail !== '',
        x, y, width: C.W, height: cardH
      })
    })

    const subIds = new Set(subs.map(n => n.id))
    for (const e of row.edges) {
      const branch = subIds.has(e.to)
      const startMagnet = vertical ? (branch ? 'RIGHT' : 'BOTTOM') : (branch ? 'BOTTOM' : 'RIGHT')
      const endMagnet = vertical ? (branch ? 'LEFT' : 'TOP') : (branch ? 'TOP' : 'LEFT')
      edges.push({ from: e.from, to: e.to, label: e.label, startMagnet, endMagnet })
    }
```

Then compute the row extents from the placed cards rather than from `main.length`, so both directions work:

```js
    const rowCards = cards.filter(c => row.nodes.some(n => n.id === c.id))
    const rowRight = Math.max(...rowCards.map(c => c.x + c.width))
    const sectionBottom = Math.max(...rowCards.map(c => c.y + c.height))
    widest = Math.max(widest, rowRight)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/Development/diagramming/skills/figma-arch-diagram/scripts && node --test`
Expected: PASS, 34 tests.

- [ ] **Step 5: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/scripts/layout.mjs skills/figma-arch-diagram/scripts/layout.test.mjs
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add top-to-bottom direction to the layout engine"
```

---

### Task 5: FigJam emitter

Turns a placement object into a real board. It makes **no layout decisions**: every coordinate is already solved.

**Files:**
- Create: `skills/figma-arch-diagram/references/emit-recipes.md`

**Interfaces:**
- Consumes: `layout()` output from Task 4; `references/component-keys.json`; `references/card-constants.json`.
- Produces: `emit-recipes.md` containing the `use_figma` snippets Tasks 6 and 7 paste and adapt, plus a real emitted diagram on a FigJam board.

Emission order matters: cards must exist before connectors can bind to them, and sections must be created before children are appended so coordinates are section-local from the start.

- [ ] **Step 1: Verify the library is published and importable**

Read `figma-use` and `figma-use-figjam` from disk first. Then, against the **FigJam board** file key the user supplies:

```js
const KEY = "f3104f19036260e65ad91752dcf52e494fcfc134"; // Google Tag Manager
try {
  const comp = await figma.importComponentByKeyAsync(KEY);
  const inst = comp.createInstance();
  const res = { ok: true, name: comp.name, w: inst.width, h: inst.height,
                children: inst.children.map(c => c.name),
                props: Object.keys(inst.componentProperties || {}) };
  inst.remove();
  return JSON.stringify(res);
} catch (e) {
  return JSON.stringify({ ok: false, error: String(e) });
}
```

Expected: `ok: true`, `w` 140, `h` 192, `children` containing `Title`, `icon`, `Id`, `Detail`. **If this fails, stop and report**: either the library is not published or the key is stale. Every later step depends on it.

- [ ] **Step 2: Emit cards and confirm placement**

```js
const CARDS = /* layout output .cards */;
const KEYS = /* component-keys.json */;
const FONT = { family: "Nunito", style: "SemiBold Italic" };
await figma.loadFontAsync(FONT);

const placed = {};
for (const c of CARDS) {
  const key = KEYS[c.category].variants[c.brand];
  if (!key) throw new Error("no component key for " + c.category + "::" + c.brand);
  const inst = (await figma.importComponentByKeyAsync(key)).createInstance();
  figma.currentPage.appendChild(inst);
  inst.x = c.x; inst.y = c.y;

  const title = inst.findOne(n => n.name === "Title");
  const id = inst.findOne(n => n.name === "Id");
  await figma.loadFontAsync(title.fontName);
  title.characters = c.title;
  id.characters = c.instance;

  if (c.showDetail) {
    const propKey = Object.keys(inst.componentProperties).find(k => k.startsWith("ShowDetail"));
    if (propKey) inst.setProperties({ [propKey]: true });
    const det = inst.findOne(n => n.name === "Detail");
    if (det) { await figma.loadFontAsync(det.fontName); det.characters = c.detail; }
  }
  placed[c.id] = inst.id;
}
return JSON.stringify({ count: Object.keys(placed).length, placed: placed });
```

Assert: the returned count equals `CARDS.length`, and every value is a node id. Keep the `placed` map; connectors need it.

- [ ] **Step 3: Emit connectors with explicit magnets**

The two traps are encoded here: a new connector's `text.fontName` is invalid until you set it, and `AUTO` magnets are forbidden.

```js
const EDGES = /* layout output .edges */;
const PLACED = /* the id map from Step 2 */;
const LABEL_FONT = { family: "Inter", style: "Medium" };
await figma.loadFontAsync(LABEL_FONT);

const made = [];
for (const e of EDGES) {
  if (e.startMagnet === "AUTO" || e.endMagnet === "AUTO") {
    throw new Error("AUTO magnet is forbidden on flow edges: " + e.from + "->" + e.to);
  }
  const conn = figma.createConnector();
  conn.connectorStart = { endpointNodeId: PLACED[e.from], magnet: e.startMagnet };
  conn.connectorEnd = { endpointNodeId: PLACED[e.to], magnet: e.endMagnet };
  conn.connectorLineType = "ELBOWED";
  conn.connectorStartStrokeCap = "NONE";
  conn.connectorEndStrokeCap = "ARROW_LINES";
  if (e.label) {
    conn.text.fontName = LABEL_FONT;   // MUST be set before characters; default is invalid
    conn.text.characters = e.label;
  }
  made.push(conn.id);
}
return JSON.stringify({ connectors: made.length });
```

Assert: `connectors` equals `EDGES.length`.

- [ ] **Step 4: Emit notes, annotations and row sections**

Notes and annotations are instances of the `Note` set, keyed by kind:

```js
const NOTES = /* layout output .notes concat .annotations */;
const NOTE_KEYS = /* component-keys.json Note.variants */;
for (const n of NOTES) {
  const inst = (await figma.importComponentByKeyAsync(NOTE_KEYS[n.kind])).createInstance();
  figma.currentPage.appendChild(inst);
  inst.x = n.x; inst.y = n.y;
  inst.resize(n.width, inst.height);
  const body = inst.findOne(t => t.name === "Body");
  await figma.loadFontAsync(body.fontName);
  body.characters = n.title ? (n.title + "\n" + n.text) : n.text;
}
```

Sections group each row visually. **A FigJam section's `name` is UI chrome and does NOT render on canvas**: it is absent from screenshots entirely. Emit a real TEXT node per row into the band reserved by `LAYOUT.ROW_TITLE_H`, or rows come out untitled. Push sections to the back with `insertChild(0, sec)` or their fills cover the diagram. Positioning a section over existing nodes does not capture them as children, so everything stays in board coordinates, but if you ever do `appendChild` to a section, append before positioning, because coordinates become section-local.

- [ ] **Step 5: Screenshot and eyeball**

`get_screenshot` on the emitted content. Confirm: rows read left-to-right, arrows land on card edges, no connector crosses a card, notes sit above their cards, annotations are in the right gutter.

- [ ] **Step 6: Write `references/emit-recipes.md`**

Capture every snippet above **as actually run**, including any corrections discovered while running them, plus the two traps stated explicitly (connector font, section-local coordinates).

- [ ] **Step 7: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/emit-recipes.md
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add FigJam emit recipes for cards, connectors, notes and sections"
```

---

### Task 6: Verification pass

The stage that makes output reliably clean rather than usually clean. It reads the board back and asserts.

**Files:**
- Create: `skills/figma-arch-diagram/references/verify.md`

**Interfaces:**
- Consumes: the emitted board and the `placed` id map from Task 5.
- Produces: `verify.md` documenting the five assertions, the read-only `use_figma` script that runs them, and the repair action for each failure.

The five assertions:

1. **No text is clipped.** For every `Title`, `Id`, `Detail` and note `Body` in the emitted content, `absoluteRenderBounds.height` must not exceed its band height (Title 40, Id 20, Detail 80). **Node dimensions are not evidence**: a wrapping text node keeps its declared size. Repair: shorten the offending string, or set `showDetail` and move prose to the detail band.
2. **No two cards overlap.** Pairwise bounding-box test over every emitted instance. Repair: the layout engine has a bug; fix `layout.mjs` and re-emit rather than nudging in Figma.
3. **Cards in a row share `y` and `height`.** Group by the row section they belong to. Repair: as above.
4. **Every connector is attached at both ends.** `connectorStart.endpointNodeId` and `connectorEnd.endpointNodeId` must both be set; a floating endpoint means the target was missing at emit time. Repair: re-emit that edge.
5. **No connector uses an `AUTO` magnet.** Repair: re-emit with the magnet the layout engine specified.

- [ ] **Step 1: Write the verification script and run it against Task 5's board**

```js
const ROOT = await figma.getNodeByIdAsync(CONTENT_NODE_ID);
const BANDS = { Title: 40, Id: 20, Detail: 80, Body: 9999 };
const insts = ROOT.findAll(n => n.type === "INSTANCE");
const conns = ROOT.findAll(n => n.type === "CONNECTOR");

const clipped = [], overlaps = [], floating = [], autoMagnets = [];
for (const i of insts) {
  for (const t of i.findAll(n => n.type === "TEXT")) {
    const cap = BANDS[t.name];
    if (cap && t.absoluteRenderBounds && t.absoluteRenderBounds.height > cap + 2) {
      clipped.push({ card: i.name, band: t.name, h: Math.round(t.absoluteRenderBounds.height), cap, chars: t.characters });
    }
  }
}
for (let a = 0; a < insts.length; a++) for (let b = a + 1; b < insts.length; b++) {
  const p = insts[a], q = insts[b];
  const disjoint = p.x + p.width <= q.x || q.x + q.width <= p.x || p.y + p.height <= q.y || q.y + q.height <= p.y;
  if (!disjoint) overlaps.push([p.name, q.name]);
}
for (const c of conns) {
  if (!c.connectorStart.endpointNodeId || !c.connectorEnd.endpointNodeId) floating.push(c.id);
  if (c.connectorStart.magnet === "AUTO" || c.connectorEnd.magnet === "AUTO") autoMagnets.push(c.id);
}
return JSON.stringify({ instances: insts.length, connectors: conns.length,
                        clipped, overlaps, floating, autoMagnets });
```

Expected on a correct board: `clipped`, `overlaps`, `floating` and `autoMagnets` all empty.

- [ ] **Step 2: Prove the clipping check actually catches something**

A check that has never failed is not known to work. Temporarily set one card's `Id` to a string long enough to wrap (for example `AC1a2b3c4d5e6f7g8h`), re-run the script, and confirm that card appears in `clipped` with `h` around 27 against `cap` 20. Then restore the original value and confirm `clipped` is empty again. Record both observed outputs.

- [ ] **Step 3: Write `references/verify.md`**

Document the five assertions, the script as run, the expected clean output, the proof-of-failure result from Step 2, and the repair action per failure. State plainly that assertion 1 must use `absoluteRenderBounds` and why.

- [ ] **Step 4: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/verify.md
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add verification pass for emitted diagrams"
```

---

### Task 7: SKILL.md, installation, and an end-to-end rebuild

Makes it a real, invocable skill, and proves the whole pipeline on the diagram that motivated the project.

**Files:**
- Create: `skills/figma-arch-diagram/SKILL.md`
- Create: `skills/figma-arch-diagram/examples/e2e-tracking.json`
- Create symlink: `~/.claude/skills/figma-arch-diagram` → `~/Development/diagramming/skills/figma-arch-diagram`

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: an invocable skill and a worked example spec.

- [ ] **Step 1: Write `SKILL.md`**

Frontmatter:

```markdown
---
name: figma-arch-diagram
description: Use when building or updating architecture, tech-stack, networking, or data-flow diagrams in Figma/FigJam from the "Icon Lib - Editable" library, including requests like "diagram this stack", "map this pipeline", "show how these services connect", or updating an existing board. Places cards from the published component library, routes with native FigJam connectors, and verifies the result. Do NOT use for Mermaid or generate_diagram output.
---
```

Body must cover, in this order: the governing rule (**nothing is ever placed by hand: author a spec, run `layout.mjs`, emit solved coordinates**); the four stages with pointers to `references/spec-format.md`, `references/emit-recipes.md`, `references/verify.md`; the hard constraints (FigJam only, place by component key not node id, explicit magnets never `AUTO`, connector font must be set before characters, `absoluteRenderBounds` for text fit); and a pointer to `figma-use` / `figma-use-figjam` on disk for plugin-API mechanics rather than restating them.

- [ ] **Step 2: Author the worked example spec**

Write `examples/e2e-tracking.json`, the user's real `SHIPPED: Production since v4.21.10` row as described in Task 1 Step 5, plus the `PLANNED: CRM offline conversions` row with `Twilio`, `FastLease CRM` (Node/Framework, Laravel), `Data Manager API` (Node/API & Services, REST API), and `Google Ads` as a `lane: sub` node.

- [ ] **Step 3: Run the full pipeline end to end**

```bash
cd ~/Development/diagramming/skills/figma-arch-diagram/scripts
node --test
node -e "
import('./spec.mjs').then(async ({normalizeSpec}) => {
  const {layout} = await import('./layout.mjs')
  const fs = await import('node:fs')
  const spec = normalizeSpec(JSON.parse(fs.readFileSync('../examples/e2e-tracking.json')))
  const C = JSON.parse(fs.readFileSync('../references/card-constants.json'))
  const out = layout(spec, C)
  console.log(JSON.stringify({cards: out.cards.length, edges: out.edges.length, notes: out.notes.length, canvas: out.canvas}))
})"
```

Then emit to a FigJam board using Task 5's recipes and run Task 6's verification. **All five assertions must come back empty.**

- [ ] **Step 4: Screenshot and compare against the original**

`get_screenshot` the result. Compare against the messy original: confirm no connector crosses any text, every row shares a baseline, the fan-out drops below its row rather than through it, and annotations sit in the gutter. Send the screenshot to the user for sign-off.

- [ ] **Step 5: Install the skill**

```bash
ln -s ~/Development/diagramming/skills/figma-arch-diagram ~/.claude/skills/figma-arch-diagram
ls -la ~/.claude/skills/ | grep figma
```

Expected: a symlink pointing at the repo, matching the pattern used by `find-skills`, `vercel-cli` and `tanstack-start-best-practices`.

- [ ] **Step 6: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/SKILL.md skills/figma-arch-diagram/examples/e2e-tracking.json
git -c user.name="Sam Kumar" -c user.email="sam@skproductions.llc" commit -m "Add figma-arch-diagram skill and worked example"
```

---

## Done when

- `node --test` passes 34 tests across `spec.test.mjs` and `layout.test.mjs`.
- The example diagram is emitted to a FigJam board and all five verification assertions return empty.
- The clipping check has been proven to fail on a deliberately overflowing string and pass once restored.
- `~/.claude/skills/figma-arch-diagram` resolves and the skill appears in the skill list.

## Not in this plan

- Nested grouping boxes (VPC / trust boundaries). The spec lists them; they are deferred until the linear and branch cases are proven in use, because FigJam sections may cover the need without new engine code.
- Migrating diagrams already on canvas.
- Any change to the published component library.
