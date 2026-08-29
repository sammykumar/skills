# FigJam emit recipes

Every snippet here was run against a real FigJam board and is recorded as it actually executed. These recipes consume the `layout()` output from `scripts/layout.mjs` and make **no layout decisions**: every coordinate is already solved. If a coordinate looks wrong on the board, fix the layout engine, not the emitter.

## Prerequisites

- The board is a FigJam file (`figma.com/board/...`). `figma.createPage()` does **not** exist in FigJam, so organize with sections instead.
- Read the `figma-use` and `figma-use-figjam` skills before every `use_figma` call, and pass `skillNames: "figma-use,figma-use-figjam"`.
- The component library must be **published**. `figma.importComponentByKeyAsync(key)` resolves published keys from any file, including FigJam boards.
- Card geometry comes from `references/card-constants.json` (`W`, `H_COMPACT`, `H_EXTENDED`). Never hardcode `140` / `192` / `284`.
- Component keys come from `references/component-keys.json`.

## Emission order

Order is not stylistic; it is forced by data dependencies.

1. **Cards** first. Connectors bind to node ids, so the cards must exist and their ids must be captured.
2. **Connectors** second, using the `placed` map from step 1.
3. **Notes and annotations** third. They are independent, but they read better on top of the section fills.
4. **Sections and row titles** last, pushed to the back of the z-order.

Everything is emitted in **board coordinates**. Nothing is appended into a section. This is deliberate (see "Trap 3" below).

## Trap 1: `ShowDetail` must be set *before* you look for the `Detail` node

While `ShowDetail` is false the `Detail` node **does not exist** in the instance. It is absent, not hidden: `inst.findOne(n => n.name === "Detail")` returns `null`, and the instance's children are exactly `["Title", "icon", "Id"]`. Calling `setProperties` materializes the node and grows the card from `H_COMPACT` to `H_EXTENDED`.

This is the opposite of the natural order (find the node, then decide whether to fill it) and is the single easiest way to silently emit cards with no detail band.

**The property key suffix differs between the source component and imported instances.** On the source component it is `ShowDetail#354:0`; on an instance imported into a different file it is `ShowDetail#368:1`. Always discover it by prefix, never hardcode either value:

```js
const propKey = Object.keys(inst.componentProperties).find(k => k.startsWith("ShowDetail"));
```

## Trap 1b: drive `ShowDetail` from the layout height, not from the detail text

`ShowDetail` is a **geometry** decision, and the layout engine already made it. The engine equalizes a row to `H_EXTENDED` when *any* node in that row has detail text, so `card.height` is the authority:

```js
const wantsDetail = c.height === C.H_EXTENDED;
```

Keying off `c.detail !== ""` instead emits a ragged row: the one card with detail is 284 tall and its neighbours are 192, which is exactly the defect the Phase 1 library normalization exists to remove. **A card with an empty detail band is correct.** The band is reserved space; reserving it is what holds the row's baseline.

After emitting, assert that every card in a row shares both its top edge and its bottom edge.

## Trap 2: a new connector's `text.fontName` is invalid

`figma.loadFontAsync(connector.text.fontName)` **throws** on a freshly created connector. Load a known font, assign `connector.text.fontName` explicitly, then set `connector.text.characters`.

Setting `connector.name` changes only the layer name in the layers panel. It is invisible on canvas. The visible label is `connector.text.characters`.

(For an *existing* connector that already has text, `text.fontName` is valid and can be loaded directly.)

## Trap 3: `appendChild` to a section makes coordinates section-local

On `section.appendChild(node)` the node's `x`/`y` switch from board coordinates to section-local coordinates, where `(0,0)` is the section's top-left. If you must append, append **first**, then position, then resize the section to encompass its children.

**This skill avoids the problem entirely.** A section created and positioned over existing nodes does **not** capture them. Verified: both emitted sections reported `children: 0` while all cards remained page-level children. So sections are pure background chrome here, and every node keeps its board coordinates straight from the layout engine. Do not `appendChild` cards into row sections.

## Trap 4: a section's *name* does not render on canvas

The FigJam section name is UI chrome. It shows in the layers panel and in the FigJam UI, but it is **not** part of the canvas render: a `get_screenshot` of the board, or of the section node itself, shows no title text at all.

This is why the layout engine reserves `LAYOUT.ROW_TITLE_H` (44px) between the section's padded top edge and the first row content. **Emit a real `TEXT` node into that reserved band** or the row titles will be invisible in every export. Set the section name too, since it is still the right navigational identifier, but do not rely on it to convey the row title.

## Step 1: confirm the library is importable

Run this once against the target board before anything else. If it returns `ok: false`, stop: either the library is unpublished or the key is stale, and every later step depends on it.

```js
const KEY = "f3104f19036260e65ad91752dcf52e494fcfc134"; // Google Tag Manager
try {
  const comp = await figma.importComponentByKeyAsync(KEY);
  const inst = comp.createInstance();
  figma.currentPage.appendChild(inst);
  inst.x = -3000; inst.y = -3000;
  const res = { ok: true, name: comp.name, w: inst.width, h: inst.height,
                children: inst.children.map(c => c.name),
                props: Object.keys(inst.componentProperties || {}) };
  inst.remove();
  return JSON.stringify(res);
} catch (e) {
  return JSON.stringify({ ok: false, error: String(e) });
}
```

Expected: `ok: true`, `w: 140`, `h: 192`, `children: ["Title","icon","Id"]`, `props: ["ShowDetail#368:1","Brand"]`.

Note that `children` does **not** include `Detail`; that is Trap 1, not a failure.

## Step 2: emit cards

Split across calls if you have more than ~5 cards; each `importComponentByKeyAsync` is a network round trip. This ran as two calls (4 cards, then 3).

```js
const CARDS = /* layout output .cards, with .key resolved from component-keys.json */;
const FONT = { family: "Nunito", style: "SemiBold Italic" };
await figma.loadFontAsync(FONT);

const placed = {};
const geom = [];
for (const c of CARDS) {
  const inst = (await figma.importComponentByKeyAsync(c.key)).createInstance();
  figma.currentPage.appendChild(inst);
  inst.x = c.x; inst.y = c.y;
  inst.name = "card/" + c.id;

  // Drive ShowDetail from the height the layout engine assigned, NOT from whether
  // this card has detail text, see Trap 1b. And it MUST be set before looking for
  // the Detail node: while the property is false that node does not exist at all.
  const wantsDetail = c.height === C.H_EXTENDED;
  if (wantsDetail) {
    const propKey = Object.keys(inst.componentProperties).find(k => k.startsWith("ShowDetail"));
    if (!propKey) throw new Error("no ShowDetail property on " + c.id);
    inst.setProperties({ [propKey]: true });
  }

  const title = inst.findOne(n => n.name === "Title");
  const id = inst.findOne(n => n.name === "Id");
  await figma.loadFontAsync(title.fontName);
  title.characters = c.title;
  await figma.loadFontAsync(id.fontName);
  id.characters = c.instance;

  if (wantsDetail) {
    const det = inst.findOne(n => n.name === "Detail");
    if (!det) throw new Error("Detail node still missing after setProperties on " + c.id);
    await figma.loadFontAsync(det.fontName);
    det.characters = c.detail;   // "" is fine, the band stays reserved but empty
  }

  // The emitted card must match the height the layout solved for.
  if (inst.height !== c.height) {
    throw new Error("card " + c.id + " emitted at h=" + inst.height + ", layout expected " + c.height);
  }
  placed[c.id] = inst.id;
  geom.push({ id: c.id, nodeId: inst.id, x: inst.x, y: inst.y, w: inst.width, h: inst.height });
}
return JSON.stringify({ count: Object.keys(placed).length, placed, geom, createdNodeIds: Object.values(placed) });
```

Resolve `c.key` as `KEYS[c.category].variants[c.brand]` and throw if it is missing: a stale brand name otherwise fails deep inside `importComponentByKeyAsync` with a much worse error.

Assert `count === CARDS.length`. **Keep the `placed` map**: connectors need it and verification wants it.

All three text sublayers (`Title`, `Id`, `Detail`) use `Nunito SemiBold Italic`. Loading `title.fontName` / `id.fontName` / `det.fontName` from the node rather than hardcoding is still the right habit; it survives a library restyle.

Cards are component instances with fixed geometry. **Do not resize them.** The only lever on card height is `ShowDetail`, which is why it is driven from `c.height` (Trap 1b). That is what makes the emitted height match the solved height, and the `inst.height !== c.height` guard turns any future divergence into a loud failure instead of a ragged row.

## Step 3: emit connectors with explicit magnets

```js
const EDGES = /* layout output .edges */;
const PLACED = /* the id map from Step 2, inlined as a literal */;
const LABEL_FONT = { family: "Inter", style: "Medium" };
await figma.loadFontAsync(LABEL_FONT);

const made = [];
for (const e of EDGES) {
  if (e.startMagnet === "AUTO" || e.endMagnet === "AUTO") {
    throw new Error("AUTO magnet is forbidden on flow edges: " + e.from + "->" + e.to);
  }
  if (!PLACED[e.from] || !PLACED[e.to]) throw new Error("unplaced endpoint: " + e.from + "->" + e.to);

  const conn = figma.createConnector();
  conn.connectorStart = { endpointNodeId: PLACED[e.from], magnet: e.startMagnet };
  conn.connectorEnd = { endpointNodeId: PLACED[e.to], magnet: e.endMagnet };
  conn.connectorLineType = "ELBOWED";
  conn.connectorStartStrokeCap = "NONE";
  conn.connectorEndStrokeCap = "ARROW_LINES";
  conn.name = "edge/" + e.from + "->" + e.to;
  if (e.label) {
    // A new connector's text.fontName is invalid; assign it before characters.
    conn.text.fontName = LABEL_FONT;
    conn.text.characters = e.label;
  }
  made.push({ id: conn.id, edge: e.from + "->" + e.to, label: conn.text.characters });
}
return JSON.stringify({ connectors: made.length, made, createdNodeIds: made.map(m => m.id) });
```

**The `AUTO` guard is the whole reason this skill exists, so keep it.** `AUTO` lets Figma re-pick attachment points as the board changes, which is exactly the non-determinism the layout engine was built to remove. The magnets in the layout output are load-bearing.

`figma.createConnector()` auto-appends to the current page; no explicit `appendChild` is needed.

An edge with no label leaves `conn.text.characters` as `""`, so do not set the font on unlabelled connectors, there is nothing to render.

## Step 4: emit notes and annotations

`notes` and `annotations` are both instances of the `Note` variant set, keyed by `kind` (`warn` / `broken` / `ok`). Annotations additionally carry a `title`; join it to the text with a newline into the single `Body` node.

The `Note` instance is a **VERTICAL auto-layout**, 140x36 by default, containing a `Row` frame that is `layoutSizingHorizontal: "FILL"`, which contains the `Body` text at `textAutoResize: "HEIGHT"`. That chain means resizing the instance's width reflows `Body` automatically and the height hugs the result, with no manual child sizing needed.

```js
const NOTE_KEYS = /* component-keys.json Note.variants */;
const NOTES = /* layout output .notes concat .annotations */;

const made = [];
for (const n of NOTES) {
  const inst = (await figma.importComponentByKeyAsync(NOTE_KEYS[n.kind])).createInstance();
  figma.currentPage.appendChild(inst);
  inst.name = "note/" + n.kind + (n.title ? "/" + n.title : "");

  // Width first so the text reflows at final width, height hugs afterwards.
  inst.resize(n.width, inst.height);

  const body = inst.findOne(t => t.name === "Body");
  await figma.loadFontAsync(body.fontName);
  body.characters = n.title ? (n.title + "\n" + n.text) : n.text;

  inst.primaryAxisSizingMode = "AUTO";   // VERTICAL auto-layout: primary axis is height -> hug

  inst.x = n.x; inst.y = n.y;
  made.push({ id: inst.id, kind: n.kind, x: inst.x, y: inst.y, w: inst.width, h: inst.height });
}
return JSON.stringify({ notes: made.length, made, createdNodeIds: made.map(m => m.id) });
```

Two details worth keeping:

- **Resize before setting text, position after.** Setting the width first means `Body` wraps at its final width, so the hugged height is correct the first time.
- `resize()` on this instance **preserved** `primaryAxisSizingMode: "AUTO"` rather than forcing it to `FIXED`: the observed values after `resize()` were `primary: "AUTO", counter: "FIXED"`. The explicit re-set is therefore a no-op guard here, but keep it: it costs nothing and protects against the general rule that `resize()` pins sizing modes.

Observed results: a 140-wide note hugged to 50px tall; 260-wide annotations hugged to 65px.

## Step 5: emit row sections, then row titles

Sections are created last and pushed to the **back** of the z-order. They are appended to the page like any node, which puts them on top and hides the diagram until you move them.

```js
const h = (r, g, b) => ({ r: r / 255, g: g / 255, b: b / 255 });
const SECTIONS = /* layout output .sections, with a fill chosen per row */;

const made = [];
for (const s of SECTIONS) {
  const sec = figma.createSection();
  sec.name = s.title;
  sec.resize(s.width, s.height);
  sec.x = s.x; sec.y = s.y;
  sec.fills = [{ type: "SOLID", color: s.fill }];
  // Sections are appended last, so they land on top of the cards. Push each to the
  // back of the page so the diagram content stays visible.
  figma.currentPage.insertChild(0, sec);
  made.push({ id: sec.id, title: sec.name, children: sec.children.length });
}
return JSON.stringify({ sections: made.length, made, createdNodeIds: made.map(m => m.id) });
```

Assert `children === 0` on every section. A non-zero count means something got captured and its coordinates are now section-local.

Use `hex/255` notation for fills (`h(0xf5, 0xfb, 0xff)`), because rounded decimals make FigJam treat the color as "custom" rather than a palette color. Vary the fill across rows.

Then the visible row titles, into the band the engine reserved (Trap 4):

```js
const SECTION_PAD = 40;   // LAYOUT.SECTION_PAD from layout.mjs
const ROW_TITLE_H = 44;   // LAYOUT.ROW_TITLE_H from layout.mjs
const TITLE_FONT = { family: "Inter", style: "Semi Bold" };
await figma.loadFontAsync(TITLE_FONT);

const made = [];
for (const s of SECTIONS) {
  const t = figma.createText();
  figma.currentPage.appendChild(t);
  t.fontName = TITLE_FONT;
  t.fontSize = 22;
  t.characters = s.title;
  t.name = "rowtitle/" + s.id;
  t.fills = [{ type: "SOLID", color: h(0x1e, 0x1e, 0x1e) }];
  // The engine reserves ROW_TITLE_H between the section's padded top edge and the
  // first row content; drop the title into that band, vertically centred.
  t.x = s.x + SECTION_PAD;
  t.y = s.y + SECTION_PAD + (ROW_TITLE_H - t.height) / 2;
  made.push({ id: t.id, title: s.title, x: t.x, y: t.y, w: t.width, h: t.height });
}
return JSON.stringify({ titles: made.length, made, createdNodeIds: made.map(m => m.id) });
```

Import `SECTION_PAD` and `ROW_TITLE_H` from `LAYOUT` in `scripts/layout.mjs` and inline them as literals; do not invent them. The title position is derived from constants the engine already owns, so this stays consistent with the rest of the placement.

Inter's semibold style string is `"Semi Bold"`, with a space; `"SemiBold"` throws. (The card library's Nunito style is `"SemiBold Italic"`, no space. The two conventions differ per family; verify with `listAvailableFontsAsync()` rather than guessing.)

## Step 6: verify

`get_metadata` does **not** work on FigJam. Use `get_figjam` for the node tree, `get_screenshot` for the render, and a read-only `use_figma` for assertions:

```js
const kids = figma.currentPage.children;
const byType = {};
for (const k of kids) byType[k.type] = (byType[k.type] || 0) + 1;

const conns = kids.filter(k => k.type === "CONNECTOR").map(c => ({
  name: c.name,
  startId: c.connectorStart.endpointNodeId, startMagnet: c.connectorStart.magnet,
  endId: c.connectorEnd.endpointNodeId, endMagnet: c.connectorEnd.magnet,
  label: c.text.characters
}));
const autoMagnets = conns.filter(c => c.startMagnet === "AUTO" || c.endMagnet === "AUTO").map(c => c.name);
const unbound = conns.filter(c => !c.startId || !c.endId).map(c => c.name);
const brokenInstances = kids.filter(k => k.type === "INSTANCE" && !k.mainComponent).map(k => k.name);

return JSON.stringify({ byType, total: kids.length, autoMagnets, unbound, brokenInstances, conns });
```

Assert `autoMagnets`, `unbound` and `brokenInstances` are all empty, and that `byType` matches the placement: one `INSTANCE` per card plus one per note/annotation, one `CONNECTOR` per edge, one `SECTION` and one `TEXT` per row.

Also assert the **row baseline**: every card in a row shares a top edge and a bottom edge:

```js
const MAIN = /* { rowId: [main-lane card ids] } */;
const cards = {};
for (const k of figma.currentPage.children) if (k.type === "INSTANCE" && k.name.startsWith("card/")) cards[k.name.slice(5)] = k;
const baselines = {};
for (const [row, ids] of Object.entries(MAIN)) {
  baselines[row] = {
    tops: [...new Set(ids.map(i => cards[i].y))],
    bottoms: [...new Set(ids.map(i => cards[i].y + cards[i].height))]
  };
}
return JSON.stringify(baselines);   // every tops/bottoms array must have length 1
```

**Connector bounding boxes are not a usable collision test.** `conn.x/y/width/height` is the bbox of the whole elbowed route *including its text label*, so it covers a large empty rectangle and produces false positives, and the label can extend the bbox well past the line itself (measured: a cross-row connector reported `x: 131` when its actual vertical run was at x≈169, the difference being the label). The Plugin API does not expose the route polyline. **Connector-vs-card crossing has to be checked visually**, by cropping the render at the suspect band. `get_screenshot` on a single card node with `contentsOnly: false` did *not* reliably show overlapping connectors, so crop the full-board render instead.

`get_screenshot` needs a real `nodeId`; `0:1` is the FigJam root and renders the whole board. Screenshotting a row section node alone is not useful here, because sections hold no children, they render empty.

## Cross-row edge routing: unresolved

**A cross-row edge still crosses cards on the way to its target. This is open, and it is a layout-engine problem, not an emitter one.**

FigJam gives no control over where an elbowed connector bends. The bend is placed automatically, and the two facts that follow from that govern everything here:

1. A connector leaves a magnet **perpendicular to that edge, at the edge's midpoint**. So a `LEFT` magnet exits horizontally at the card's vertical centre, the same height every other card in that row sits at, since rows share a baseline.
2. When source and target need a dogleg, the bend lands at roughly the **vertical midpoint** between the two endpoints, wherever that happens to be.

All three natural magnet pairs were measured on a real board, with a spec whose cross-row source was the rightmost card of a row that also had a sub-lane card:

| Magnets | Route | Result |
|---|---|---|
| `BOTTOM` -> `TOP` | drops from the source, bends at the midpoint between the rows | bend lands inside the **sub-lane card**; label sits on the card's text |
| `LEFT` -> `LEFT` | exits left at the source's vertical centre, down the left channel, into the target's left | horizontal leg crosses **every card to the source's left in its own row**, and strikes through their edge labels |
| `BOTTOM` -> `LEFT` | drops from the source, bends at the midpoint, down the left channel | bend still lands inside the **sub-lane card** |

`LEFT` -> `LEFT` has the best *topology*: its legs are at the two cards' centre heights with a vertical run in between, so there is no midpoint bend to land badly. It is clean **if and only if the source is the leftmost card in its row**. That is the uncommon case: a cross-row edge is usually a hop to the next tier, so its source is typically the *last* card in the row, which is the worst case.

`LAYOUT.MARGIN` is set to 200 to reserve `x < MARGIN - SECTION_PAD` (160) as an empty vertical channel, left of every section, card and row title, and a test asserts nothing is placed there. That channel works; the vertical run does land in it. It is the **horizontal** legs that still cross content, and the channel cannot help with those.

Fixing this properly means making the bend land somewhere known-empty, which only the layout engine can do, for example by deriving `ROW_GAP` so the inter-row midpoint always clears the previous row's deepest sub-lane card, rather than using a fixed constant. For the measured case that needed `ROW_GAP` of about 330 rather than 140. Do not attempt to fix it in the emitter by nudging magnets; all the reachable options are in the table above.

## Other known geometry limitations

Layout-engine properties, visible on the emitted board. Recorded so nobody mistakes them for emitter bugs and "fixes" them in the wrong place.

- **Cross-row edges can cross the row-title band.** Related to the above: an edge entering the target's `TOP` passes through the reserved `ROW_TITLE_H` band and over the title text. Now that row titles are real rendered nodes, this collision is visible where it previously was not.
- **A row where any node has detail reserves `H_EXTENDED` for every card in that row**, so cards with no detail text show an empty reserved band. This is deliberate: it is what holds the row baseline (Trap 1b).

Resolved: an earlier version of these recipes noted that an edge between a compact and an extended card in the same row elbowed visibly. That was a symptom of the ragged-row bug, and it disappeared once `ShowDetail` was driven from `c.height`: with equal heights the `LEFT`/`RIGHT` magnets share a vertical centre and the connector renders as a straight line (measured `height: 0`).
