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
