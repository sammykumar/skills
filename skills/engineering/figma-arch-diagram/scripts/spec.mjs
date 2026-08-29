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
