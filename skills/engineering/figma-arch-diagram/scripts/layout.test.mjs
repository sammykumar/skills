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

test('a cross-row edge is emitted with BOTTOM to LEFT magnets', () => {
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
  assert.equal(cross.endMagnet, 'LEFT')
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

test('TB notes sit beside their card, never on top of it', () => {
  const s = normalizeSpec({ title: 'T', direction: 'TB', rows: [{ id: 'r1',
    nodes: [node('a'), node('b')],
    notes: [{ on: 'b', kind: 'warn', text: 'careful' }] }] })
  const out = layout(s, C)
  const b = out.cards.find(c => c.id === 'b')
  const nte = out.notes.find(n => n.on === 'b')
  assert.ok(nte, 'note placed')
  assert.equal(nte.y, b.y, 'aligned on its card row')
  assert.ok(nte.x + nte.width <= b.x, 'note band is clear of the card column')
  for (const c of out.cards) {
    const disjoint = nte.x + nte.width <= c.x || c.x + c.width <= nte.x ||
                     nte.y + LAYOUT.NOTE_BAND <= c.y || c.y + c.height <= nte.y
    assert.ok(disjoint, `note overlaps card ${c.id}`)
  }
})

test('cross-row edges are BOTTOM to LEFT in both directions', () => {
  for (const direction of ['LR', 'TB']) {
    const s = normalizeSpec({ title: 'T', direction,
      rows: [{ id: 'r1', nodes: [node('a')] }, { id: 'r2', nodes: [node('z')] }],
      edges: [{ from: 'a', to: 'z' }] })
    const out = layout(s, C)
    const cross = out.edges.find(e => e.from === 'a' && e.to === 'z')
    assert.equal(cross.startMagnet, 'BOTTOM', `${direction} cross-row start`)
    assert.equal(cross.endMagnet, 'LEFT', `${direction} cross-row end`)
  }
})

test('a row with an outgoing cross-row edge gets a gap clearing its deepest card', () => {
  const s = normalizeSpec({ title: 'T', rows: [
    { id: 'r1', nodes: [node('a'), node('b'), node('deep', { lane: 'sub' })],
      edges: [{ from: 'b', to: 'deep' }] },
    { id: 'r2', nodes: [node('z')] }
  ], edges: [{ from: 'a', to: 'z' }] })
  const out = layout(s, C)
  const a = out.cards.find(c => c.id === 'a')
  const z = out.cards.find(c => c.id === 'z')
  const deepest = Math.max(...out.cards.filter(c => ['a', 'b', 'deep'].includes(c.id)).map(c => c.y + c.height))
  const midpoint = (a.y + a.height + z.y) / 2
  assert.ok(midpoint > deepest + LAYOUT.CROSS_CLEARANCE - 1,
    `bend at ${midpoint} must clear deepest card at ${deepest}`)
})

test('a row with no cross-row edge keeps the normal gap', () => {
  const s = normalizeSpec({ title: 'T', rows: [
    { id: 'r1', nodes: [node('a')] }, { id: 'r2', nodes: [node('z')] } ] })
  const out = layout(s, C)
  const a = out.cards.find(c => c.id === 'a')
  const z = out.cards.find(c => c.id === 'z')
  assert.equal(z.y - (a.y + a.height), LAYOUT.ROW_GAP + LAYOUT.ROW_TITLE_H)
})

test('a cross-row edge does not inflate the gap when the row has no deeper card', () => {
  // Source is the deepest card in its row, so CROSS_CLEARANCE alone decides the gap
  // and it must never shrink below the plain ROW_GAP.
  const s = normalizeSpec({ title: 'T', rows: [
    { id: 'r1', nodes: [node('a')] }, { id: 'r2', nodes: [node('z')] }
  ], edges: [{ from: 'a', to: 'z' }] })
  const out = layout(s, C)
  const a = out.cards.find(c => c.id === 'a')
  const z = out.cards.find(c => c.id === 'z')
  assert.ok(z.y - (a.y + a.height) >= LAYOUT.ROW_GAP, 'gap never shrinks below ROW_GAP')
})

test('a row widens its column gap to fit its longest edge label', () => {
  const wide = normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('a'), node('b')],
    edges: [{ from: 'a', to: 'b', label: 'Leased / Moved-in' }] }] })
  const narrow = normalizeSpec({ title: 'T', rows: [{ id: 'r1',
    nodes: [node('a'), node('b')], edges: [{ from: 'a', to: 'b' }] }] })
  const w = layout(wide, C).cards
  const n = layout(narrow, C).cards
  const wGap = w[1].x - (w[0].x + w[0].width)
  const nGap = n[1].x - (n[0].x + n[0].width)
  assert.equal(nGap, LAYOUT.COL_GAP, 'unlabelled row keeps the default gap')
  assert.ok(wGap >= 'Leased / Moved-in'.length * LAYOUT.LABEL_CHAR_W, 'gap fits the label')
  assert.ok(wGap > nGap, 'labelled row is wider')
})
