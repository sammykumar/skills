# Verification pass

Run this after every emit. A diagram is not done until it passes.

## What is measurable, and what is not

**Text overflow is measurable, but only via `absoluteRenderBounds`.** A text node keeps its declared size when its text wraps: a `104x20` band still reports `104x20` with two lines of text in it. `node.height` is not evidence. This is the single most common way a broken diagram passes a check.

**Connector paths are NOT measurable.** `CONNECTOR` nodes have no `absoluteRenderBounds`; the property does not exist on the type. There is no route-polyline API. `conn.x/y/width/height` includes the text label, so it misreports where the line actually is (observed: reported `x: 131` for a line at `x: 169`). Any "does this connector cross a card" check built on connector coordinates will produce confident, wrong answers. **Crossing checks must be done by rendering the board and looking at it**, cropping the region if needed.

## The five assertions

| # | Assertion | How | Repair |
|---|---|---|---|
| 1 | No text is clipped | `absoluteRenderBounds.height` per band: Title 40, Id 20, Detail 80 | Shorten the string, or move prose to the detail band or a Note |
| 2 | No two cards overlap | Pairwise bounding boxes | Layout engine bug: fix `layout.mjs` and re-emit, never nudge in Figma |
| 3 | Every row shares a bottom edge | Group cards by `y`, assert one distinct bottom | Emitter must drive `ShowDetail` from `card.height`, not from whether detail text exists |
| 4 | Every connector is bound at both ends | `connectorStart/End.endpointNodeId` both set | Target was missing at emit time; re-emit that edge |
| 5 | No connector uses an `AUTO` magnet | Read both magnets | Re-emit with the magnet the layout engine specified |

Plus a **sixth, visual**: render the board and confirm no connector crosses a card, a label, or a row title. This one cannot be automated (see above).

## The script

```js
const page = figma.currentPage
const BANDS = { Title: 40, Id: 20, Detail: 80 }
const insts = page.findAll(n => n.type === "INSTANCE")
const cards = insts.filter(n => n.width === 140 && n.height >= 190)
const conns = page.findAll(n => n.type === "CONNECTOR")
const clipped = [], overlaps = [], floating = [], autoMagnets = []

for (const i of insts) {
  for (const t of i.findAll(n => n.type === "TEXT")) {
    const cap = BANDS[t.name]
    if (cap && t.absoluteRenderBounds && t.absoluteRenderBounds.height > cap + 2) {
      clipped.push(t.name + ":" + t.characters.slice(0, 28) + " h=" + Math.round(t.absoluteRenderBounds.height) + ">" + cap)
    }
  }
}
for (let a = 0; a < cards.length; a++) for (let b = a + 1; b < cards.length; b++) {
  const p = cards[a], q = cards[b]
  const d = p.x + p.width <= q.x || q.x + q.width <= p.x || p.y + p.height <= q.y || q.y + q.height <= p.y
  if (!d) overlaps.push(p.name + "/" + q.name)
}
for (const c of conns) {
  if (!c.connectorStart.endpointNodeId || !c.connectorEnd.endpointNodeId) floating.push(c.id)
  if (c.connectorStart.magnet === "AUTO" || c.connectorEnd.magnet === "AUTO") autoMagnets.push(c.id)
}
const rows = {}
for (const c of cards) { const k = Math.round(c.y); (rows[k] = rows[k] || []).push(Math.round(c.y + c.height)) }
const raggedRows = Object.keys(rows).filter(k => new Set(rows[k]).size > 1)

return JSON.stringify({ cards: cards.length, connectors: conns.length, clipped, overlaps, floating, autoMagnets, raggedRows })
```

A clean board returns every list empty.

## Proof the clipping check works

A check that has never failed is not known to work. Setting one card's `Id` to `AC1a2b3c4d5e6f7g8h9i` produced `Id:AC1a2b3c4d5e6f7g8h9i h=30>20`; restoring the original returned `clipped: []`. Re-run this proof if you ever change the band constants.
