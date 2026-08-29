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
  MARGIN: 60,
  // Vertical clearance a cross-row edge's midpoint bend must keep below the deepest
  // card of the row it leaves. FigJam chooses the bend itself, so the only way to
  // keep it off the content is to push the next row far enough down.
  CROSS_CLEARANCE: 40,
  LABEL_CHAR_W: 7,      // approx px per char for edge labels at the connector label size
  LABEL_PAD: 32         // breathing room either side of a label inside the column gap
}

export function layout (spec, C) {
  const cards = []
  const edges = []
  const sections = []
  const notes = []
  const annotations = []

  let cursorY = LAYOUT.MARGIN
  let widest = 0

  for (const row of spec.rows) {
    const main = row.nodes.filter(n => n.lane === 'main')
    const subs = row.nodes.filter(n => n.lane === 'sub')
    const rowHasDetail = row.nodes.some(n => n.detail !== '')
    const cardH = rowHasDetail ? C.H_EXTENDED : C.H_COMPACT
    const hasNotes = row.notes.length > 0

    const vertical = spec.direction === 'TB'

    // An edge label sits at the connector midpoint, i.e. inside the column gap. If the label is
    // wider than the gap it renders on top of the neighbouring cards. Widen the gap for this row
    // to fit its longest label. Rows with no labels keep COL_GAP.
    const longest = Math.max(0, ...row.edges.map(e => (e.label || '').length))
    const colGap = Math.max(LAYOUT.COL_GAP, longest * LAYOUT.LABEL_CHAR_W + LAYOUT.LABEL_PAD)

    const sectionTop = cursorY
    const noteY = sectionTop + LAYOUT.ROW_TITLE_H
    const cardsY = (hasNotes && !vertical) ? noteY + LAYOUT.NOTE_BAND + LAYOUT.NOTE_GAP : noteY
    const noteShift = (vertical && hasNotes) ? (C.W + LAYOUT.NOTE_GAP) : 0

    const colX = {}
    const colY = {}
    main.forEach((n, i) => {
      const x = vertical ? LAYOUT.MARGIN + noteShift : LAYOUT.MARGIN + i * (C.W + colGap)
      const y = vertical ? cardsY + i * (cardH + colGap) : cardsY
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
      notes.push({
        id: `note-${n.on}`, on: n.on, kind: n.kind, text: n.text,
        x: vertical ? LAYOUT.MARGIN : colX[n.on],
        y: vertical ? colY[n.on] : noteY,
        width: C.W
      })
    }

    subs.forEach((n, i) => {
      const feeder = row.edges.find(e => e.to === n.id)
      const src = feeder ? feeder.from : null
      const x = vertical
        ? (src !== null ? colX[src] + C.W + LAYOUT.SUBROW_GAP : LAYOUT.MARGIN + C.W + LAYOUT.SUBROW_GAP)
        : (src !== null ? colX[src] : LAYOUT.MARGIN + i * (C.W + colGap))
      const y = vertical
        ? (src !== null ? colY[src] : cardsY + i * (cardH + colGap))
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

    const rowCards = cards.filter(c => row.nodes.some(n => n.id === c.id))
    const rowRight = Math.max(...rowCards.map(c => c.x + c.width))
    const sectionBottom = Math.max(...rowCards.map(c => c.y + c.height))
    widest = Math.max(widest, rowRight)
    sections.push({
      id: row.id, title: row.title,
      x: LAYOUT.MARGIN - LAYOUT.SECTION_PAD,
      y: sectionTop - LAYOUT.SECTION_PAD,
      width: (rowRight - LAYOUT.MARGIN) + LAYOUT.SECTION_PAD * 2,
      height: (sectionBottom - sectionTop) + LAYOUT.SECTION_PAD * 2
    })

    // A row that is the source of a cross-row edge needs the NEXT row pushed far
    // enough down that FigJam's midpoint bend clears this row's deepest card. Only
    // such rows pay for it; every other row keeps the plain ROW_GAP.
    const rowIds = new Set(row.nodes.map(n => n.id))
    const sources = spec.edges.filter(e => rowIds.has(e.from) && !rowIds.has(e.to))
    let nextTop = sectionBottom + LAYOUT.ROW_GAP
    if (sources.length) {
      // The shallowest source is the worst case: it pulls the midpoint up.
      const srcBottom = Math.min(...sources.map(e => {
        const c = cards.find(k => k.id === e.from)
        return c.y + c.height
      }))
      // midpoint(srcBottom, nextTop) must exceed sectionBottom + CROSS_CLEARANCE.
      // The target card's top is lower still, by SECTION_PAD + ROW_TITLE_H, which
      // only adds margin, so the inequality holds a fortiori.
      nextTop = Math.max(nextTop, 2 * (sectionBottom + LAYOUT.CROSS_CLEARANCE) - srcBottom)
    }
    cursorY = nextTop
  }

  // Rows stack vertically in both directions, so a cross-row edge is always a vertical
  // hop. The gap below a row with outgoing cross-row edges is derived (see
  // CROSS_CLEARANCE) so FigJam's midpoint bend lands below that row's deepest card.
  for (const e of spec.edges) {
    // BOTTOM->LEFT: the drop clears the source row (see CROSS_CLEARANCE) and the target is
    // entered from the side, below its row-title band. TOP would enter at the card's horizontal
    // centre, which is exactly where the row title sits, and the descent would strike through it.
    edges.push({ from: e.from, to: e.to, label: e.label, startMagnet: 'BOTTOM', endMagnet: 'LEFT' })
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
}
