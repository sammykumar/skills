# Figma Library Normalization Implementation Plan

Status: implemented. Phase 1 of the design record in [`2026-07-29-figma-arch-diagram-design.md`](./2026-07-29-figma-arch-diagram-design.md), rebuilding the Figma card library the skill places from. Imported 2026-08-29 from the standalone `diagramming` repo, which was folded into this one and deleted.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the ~117 brand components in `Icon Lib - Editable` as fixed-band cards with exactly two heights, and add a `Note` component set, so that diagram rows share a baseline structurally rather than by correction.

**Architecture:** All work happens on a **new `Components v2` page** inside the existing file, created with `figma.createPage()`. The ~117 original components are never mutated; rollback is deleting one page. Each task mutates Figma through a single `use_figma` call and ends with an assertion script that must return `PASS`, plus a screenshot for visual confirmation. Measurements and inventory are captured back to JSON files in this repo so Phase 2's layout engine can consume them without re-reading Figma.

**Tech Stack:** Figma Plugin API via the `figma-personal` MCP server (`use_figma`, `get_metadata`, `get_screenshot`); JSON artifacts committed to `~/Development/diagramming`.

## Global Constraints

- **File:** `fileKey oGJ5pTR4dQI0EJhKDvdELz` ("Icon Lib - Editable"). **No node on the original `Components` page (`0:1`) is ever mutated, moved, or deleted.** Cloning *from* it is expected and fine. Every write goes to the new `Components v2` page. The single exception is renaming the page itself in Task 6 Step 4, which happens only after explicit sign-off and changes no component.
- **Load the `figma-use` skill before every `use_figma` call.** It is mandatory and covers plugin-API mechanics this plan does not restate. It is **not** registered as an invocable Skill in this environment, so read it from disk at `/Users/samkumar/.claude/plugins/cache/claude-plugins-official/figma/2.2.81/skills/figma-use/SKILL.md`, with its reference files in the sibling `references/` directory.
- **Text is Nunito SemiBold Italic at fontSize 15** throughout the existing library (verified across all 118 text nodes in Task 1: no exceptions, no mixed styling). Line height is 20, so a 1-line label is 20 tall, 2 lines 40, 3 lines 60.
- **Card width is 140 and does not change.**
- **Existing spacing model is preserved:** 18px outer padding on all four sides, 12px gap between bands, 20px per line of text, text blocks 104 wide at x=18.
- **Never mutate a node on the original `Components` page.** Clone into `Components v2` first.
- **Node IDs are not stable across clones.** Never hold a reference to a cloned node's children across multiple mutations in one `use_figma` call; re-fetch by ID in a second call. (Known failure: `in get_name: The node with id X does not exist`.)
- **`use_figma` returns its result as text.** Anything that must persist locally is echoed as JSON and written to this repo with the Write tool.
- **`PAGE_ID`** throughout this plan means the `Components v2` page id returned by Task 2 Step 1. Record it in `card-constants.json` as `"v2PageId"` in that same step so later tasks and later sessions can resolve it.
- **The base card is auto-layout.** Card height is never set directly; it is the sum of its bands. This is what makes `H_COMPACT` and `H_EXTENDED` both real: showing the `Detail` band grows the card by `GAP + DETAIL_H` automatically.

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/figma-arch-diagram/references/library-inventory.json` | Created Task 1. Every brand: component id, set id, set name, current height, icon frame id + bbox, label node ids + line counts. The source of truth for Task 5's batch transform and Phase 2's brand lookup. |
| `skills/figma-arch-diagram/references/brand-samples.json` | Authored up front. Per-brand placeholder for the instance-ID band, keyed set name → brand name. Covers all 117 brands. Task 5 reads it; a missing key is a hard error, never a fallback. |
| `skills/figma-arch-diagram/references/card-constants.json` | Created Task 2. The locked band geometry: `ICON_H`, `H_COMPACT`, `H_EXTENDED`, band offsets. Phase 2's layout engine imports this. |
| `skills/figma-arch-diagram/references/library-map.md` | Created Task 6. Human-readable category → component-set-id map with the brand inventory. |
| `docs/plans/2026-07-29-library-normalization.md` | This plan. |

---

### Task 1: Capture the library inventory

Establishes ground truth before anything is mutated, and resolves one open structural question: whether the `Node/*` containers are true `COMPONENT_SET`s (variants of a `Brand` property) or plain `FRAME`s holding loose components that happen to be named `Brand=X`. Task 5's transform differs materially between the two, so this must be answered with `node.type`, not inferred from naming.

**Files:**
- Create: `skills/figma-arch-diagram/references/library-inventory.json`

**Interfaces:**
- Produces: `library-inventory.json` with shape
  ```json
  {
    "fileKey": "oGJ5pTR4dQI0EJhKDvdELz",
    "capturedAt": "2026-07-29",
    "sets": [
      { "id": "307:318", "name": "Node/Content & Marketing", "type": "COMPONENT_SET" | "FRAME", "variantProperty": "Brand" | null,
        "brands": [
          { "id": "307:210", "name": "Brand=Sanity", "brand": "Sanity", "height": 140,
            "icon": { "id": "307:211", "iconLayerName": "icon", "x": 25, "y": 18, "w": 90, "h": 72, "shape": "chrome" | "cylinder" | "other" },
            "labels": [ { "id": "307:221", "name": "Label", "x": 18, "y": 102, "w": 104, "h": 20, "lines": 1,
                          "chars": "Sanity", "fontName": {"family":"Nunito","style":"SemiBold Italic"}, "fontSize": 18 } ] } ] } ]
  }
  ```
  Task 5 consumes `sets[].brands[]`. Task 2 consumes `icon.h` to find the maximum.

- [ ] **Step 1: Write the inventory-extraction script and run it**

Load the `figma-use` skill first. Then one `use_figma` call against `fileKey oGJ5pTR4dQI0EJhKDvdELz`:

```js
const SET_IDS = ["307:318","307:372","308:543","333:165","307:580","307:759",
                 "308:349","308:458","308:571","310:383","315:319","308:605","309:518"];

function lines(t) { return Math.max(1, Math.round(t.height / 20)); }

function shapeOf(icon) {
  const kids = icon.children ? icon.children.map(c => c.name) : [];
  if (kids.indexOf("Bottom") >= 0 && kids.indexOf("Top") >= 0 && kids.indexOf("Ellipse 1") >= 0) return "chrome";
  if (icon.height > 100) return "cylinder";
  return "other";
}

const sets = [];
// Icon layers are not uniformly named: Node/Server uses "Rack". Never hardcode "icon".
function findIcon(c) {
  return c.findChild(n => n.name === "icon")
      || c.findChild(n => n.name === "Rack")
      || c.findChild(n => n.type !== "TEXT");
}

for (const sid of SET_IDS) {
  const set = await figma.getNodeByIdAsync(sid);
  const brands = [];
  for (const c of set.children) {
    if (c.type !== "COMPONENT") continue;
    const icon = findIcon(c);
    const labels = c.children.filter(n => n.type === "TEXT").map(t => ({
      id: t.id, name: t.name, x: Math.round(t.x - c.x), y: Math.round(t.y - c.y),
      w: Math.round(t.width), h: Math.round(t.height), lines: lines(t),
      chars: t.characters, fontName: t.fontName, fontSize: t.fontSize
    }));
    brands.push({
      id: c.id, name: c.name, brand: c.name.replace(/^Brand=/, ""),
      height: c.height,
      icon: icon ? { id: icon.id, iconLayerName: icon.name,
                     x: Math.round(icon.x - c.x), y: Math.round(icon.y - c.y),
                     w: icon.width, h: icon.height, shape: shapeOf(icon) } : null,
      labels: labels
    });
  }
  sets.push({ id: set.id, name: set.name, type: set.type,
              variantProperty: set.type === "COMPONENT_SET"
                ? Object.keys(set.componentPropertyDefinitions)[0] : null,
              brands: brands });
}
return JSON.stringify({ fileKey: "oGJ5pTR4dQI0EJhKDvdELz", capturedAt: "2026-07-29", sets: sets });
```

- [ ] **Step 2: Verify the extraction is complete**

Check the returned JSON against these known-correct values before writing anything to disk:

| Assertion | Expected |
|---|---|
| `sets.length` | 13 |
| total brands across all sets | 117 |
| every `brands[].height` present | no nulls |
| every brand `icon` non-null | no nulls |
| `Node/Language` brand count | 17 |
| `Node/Adobe Experience Cloud` brand count | 21 |
| `Brand=Postgres` `icon.h` | 112.5, `shape: "cylinder"` |
| `Brand=Sanity` `icon.h` | 72, `shape: "chrome"` |
| `Brand=Google Tag Manager` `labels.length` | 2 |

If total brands ≠ 117, do not proceed; re-read the page with `get_metadata` on `0:1` and reconcile the set list before continuing. A short inventory means a set was missed and Task 5 would silently skip those brands.

- [ ] **Step 3: Write the inventory to the repo**

Write the returned JSON verbatim to `skills/figma-arch-diagram/references/library-inventory.json`.

- [ ] **Step 4: Record the structural finding**

Append a short note to the top of the plan's Task 5 (edit this file) stating whether `sets[].type` came back `COMPONENT_SET` or `FRAME`, because Task 5 branches on it:
- `COMPONENT_SET` → Task 5 clones the set and edits variants in place.
- `FRAME` → Task 5 must additionally call `figma.combineAsVariants(components, parent)` to build real sets, and Phase 2 can then use `setProperties({ Brand: "..." })`.

- [ ] **Step 5: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/library-inventory.json docs/plans/2026-07-29-library-normalization.md
git commit -m "Capture Figma icon library inventory before normalization"
```

---

### Task 2: Lock the card geometry (gated on visual sign-off)

The icon band must fit both a 72-tall browser chrome and a 112.5-tall cylinder. That single number sets the card height for all 117 components, and there is no analytically correct answer; it is a visual trade-off between compactness and data-store legibility. This task renders the candidates and gets a decision.

**Files:**
- Create: `skills/figma-arch-diagram/references/card-constants.json`

**Interfaces:**
- Consumes: `library-inventory.json` (`icon.h` max = **113**, from the `Node/Server` "Rack" frames at 99×113; the `Node/Data Store` cylinders are 99.12×112.5, just under).
- Produces: `card-constants.json`
  ```json
  { "W": 140, "PAD": 18, "GAP": 12, "LINE_H": 20,
    "TITLE_Y": 18, "TITLE_H": 40,
    "ICON_Y": 70, "ICON_H": 0,
    "ID_Y": 0, "ID_H": 20,
    "DETAIL_Y": 0, "DETAIL_H": 80,
    "H_COMPACT": 0, "H_EXTENDED": 0,
    "CHROME_SCALE": 1, "CYLINDER_SCALE": 1,
    "v2PageId": "", "baseComponentId": "", "noteSetId": "" }
  ```
  Every zero and empty string above is filled in as it becomes known: `v2PageId` at Step 4 of this task, `baseComponentId` in Task 3, `noteSetId` in Task 4. Task 3, Task 5, and Phase 2's layout engine all import this file. The `*_Y` offsets are informational only once the card is auto-layout; they describe the resulting geometry for the layout engine, they are not set on any node.

The three candidates, using the fixed model `H = PAD + TITLE_H + GAP + ICON_H + GAP + ID_H + PAD`:

| Candidate | `ICON_H` | Cylinder | Chrome | `H_COMPACT` | Trade-off |
|---|---|---|---|---|---|
| **A: normalize down** | 72 | scaled to 0.64 | native | **192** | Exactly matches the `Google Tag Manager` exemplar. Most compact. Data stores become visibly small. |
| **B: middle** | 96 | scaled to 0.85 | native | **216** | Cylinders stay readable, cards stay moderate. |
| **C: normalize up** | 114 | native | native | **234** | No artwork is ever rescaled; 114 clears the true 113 max. Highest fidelity. Cards are 67% taller than today's 140. |

`H_EXTENDED = H_COMPACT + GAP + DETAIL_H` = 284 / 308 / 326 respectively.

- [ ] **Step 1: Create the v2 page and a proof sheet**

Load `figma-use`. One `use_figma` call:

```js
const page = figma.createPage();
page.name = "Components v2";
await figma.setCurrentPageAsync(page);   // the sync setter throws inside use_figma

const src = { chrome: "307:210", cylinder: "310:242" };  // Sanity, Postgres
const CANDIDATES = [
  { key: "A", ICON_H: 72,  label: "A · ICON_H 72 · H 192" },
  { key: "B", ICON_H: 96,  label: "B · ICON_H 96 · H 216" },
  { key: "C", ICON_H: 114, label: "C · ICON_H 114 · H 234" }
];
const PAD = 18, GAP = 12, TITLE_H = 40, ID_H = 20, W = 140;

let x = 0;
for (const cand of CANDIDATES) {
  const H = PAD + TITLE_H + GAP + cand.ICON_H + GAP + ID_H + PAD;
  let y = 0;
  for (const kind of ["chrome", "cylinder"]) {
    const orig = await figma.getNodeByIdAsync(src[kind]);
    const card = orig.clone();
    card.name = `proof/${cand.key}/${kind}`;
    page.appendChild(card);
    card.x = x; card.y = y;
    card.resize(W, H);

    const icon = card.findChild(n => n.name === "icon");
    const scale = Math.min(1, cand.ICON_H / icon.height);
    if (scale < 1) icon.rescale(scale);
    icon.x = card.x + (W - icon.width) / 2;
    icon.y = card.y + PAD + TITLE_H + GAP + (cand.ICON_H - icon.height) / 2;

    y += H + 40;
  }
  x += W + 60;
}
figma.currentPage.selection = [];
return JSON.stringify({ pageId: page.id, ok: true });
```

Record the returned `pageId` immediately: it is `PAGE_ID` for every later task, and it goes into `card-constants.json` as `"v2PageId"` at Step 4.

- [ ] **Step 2: Screenshot the proof sheet**

Call `get_screenshot` on the returned `pageId` with `maxDimension: 1400`, download the PNG, and view it.

- [ ] **Step 3: Present to Sam and get the decision**

Show the screenshot with the trade-off table above. Ask which candidate to lock using AskUserQuestion with `multiSelect: true`. **Do not proceed past this step without an answer**: 117 components get rebuilt against this number.

- [ ] **Step 4: Write the locked constants**

With the chosen `ICON_H`, compute and write `card-constants.json`:

```
ICON_Y      = 70                                  (PAD 18 + TITLE_H 40 + GAP 12)
ID_Y        = ICON_Y + ICON_H + GAP
H_COMPACT   = ID_Y + ID_H + PAD
DETAIL_Y    = ID_Y + ID_H + GAP
H_EXTENDED  = DETAIL_Y + DETAIL_H + PAD
CYLINDER_SCALE = min(1, ICON_H / 113)     // 113 = true library max (Node/Server "Rack", 99x113)
CHROME_SCALE   = min(1, ICON_H / 72)
```

- [ ] **Step 5: Delete the proof cards**

```js
const page = await figma.getNodeByIdAsync(PAGE_ID);
for (const c of page.children.filter(n => n.name.startsWith("proof/"))) c.remove();
return JSON.stringify({ remaining: page.children.length });
```

Expected: `remaining: 0`.

- [ ] **Step 6: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/card-constants.json
git commit -m "Lock normalized card geometry constants"
```

---

### Task 3: Build the `Node/_Base` card component

One master card that every brand is rebuilt from, so band geometry is defined in exactly one place.

**Files:**
- Modify: `Components v2` page in Figma (no repo files)

**Interfaces:**
- Consumes: `card-constants.json` from Task 2.
- Produces: a `COMPONENT` named `Node/_Base` on `Components v2` with children named exactly `Title` (TEXT), `icon` (FRAME, empty), `Id` (TEXT), `Detail` (TEXT). Task 5 clones this and injects artwork. The child names are the contract: Task 5 and Phase 2's emitter both look children up by these names.

- [ ] **Step 1: Create the base component**

Load `figma-use`. Fonts must be loaded before setting any text.

```js
const C = /* paste card-constants.json */;
const page = await figma.getNodeByIdAsync(PAGE_ID);
const FONT = { family: "Nunito", style: "SemiBold Italic" };
await figma.loadFontAsync(FONT);

const base = figma.createComponent();
base.name = "Node/_Base";
base.cornerRadius = 14;
base.fills = [{ type: "SOLID", color: { r: 0.984, g: 0.984, b: 0.984 } }];
base.strokes = [{ type: "SOLID", color: { r: 0.2, g: 0.212, b: 0.22 } }];
base.strokeWeight = 2;
page.appendChild(base);

// Auto-layout: height is the sum of the bands, so ShowDetail actually grows the card.
base.layoutMode = "VERTICAL";
base.counterAxisSizingMode = "FIXED";
base.primaryAxisSizingMode = "AUTO";
base.counterAxisAlignItems = "CENTER";
base.paddingTop = C.PAD; base.paddingBottom = C.PAD;
base.paddingLeft = C.PAD; base.paddingRight = C.PAD;
base.itemSpacing = C.GAP;
base.resize(C.W, base.height);

function mkText(name, h, size) {
  const t = figma.createText();
  t.fontName = FONT; t.name = name; t.fontSize = size;
  t.textAlignHorizontal = "CENTER"; t.textAlignVertical = "CENTER";
  t.characters = name;
  t.textAutoResize = "NONE";
  t.fills = [{ type: "SOLID", color: { r: 0.2, g: 0.212, b: 0.22 } }];
  base.appendChild(t);
  t.layoutSizingHorizontal = "FILL";
  t.resize(t.width, h);
  return t;
}

mkText("Title", C.TITLE_H, 15);   // 15 = the library-wide size verified in Task 1

// Icon slot is itself auto-layout+centred, so artwork of any size self-centres in Task 5.
const iconFrame = figma.createFrame();
iconFrame.name = "icon";
iconFrame.fills = [];
base.appendChild(iconFrame);
iconFrame.layoutMode = "HORIZONTAL";
iconFrame.primaryAxisAlignItems = "CENTER";
iconFrame.counterAxisAlignItems = "CENTER";
iconFrame.primaryAxisSizingMode = "FIXED";
iconFrame.counterAxisSizingMode = "FIXED";
iconFrame.clipsContent = false;
iconFrame.layoutSizingHorizontal = "FILL";
iconFrame.resize(iconFrame.width, C.ICON_H);

mkText("Id", C.ID_H, 13);
const detail = mkText("Detail", C.DETAIL_H, 11);
detail.visible = false;

return JSON.stringify({ id: base.id, w: base.width, h: base.height,
                        children: base.children.map(c => c.name) });
```

- [ ] **Step 2: Assert the base component is correct**

Expected from Step 1's return:
- `w` === `C.W` (140)
- `h` === `C.H_COMPACT`
- `children` === `["Title", "icon", "Id", "Detail"]`

If `children` is in a different order or misnamed, fix and re-run; Task 5 looks these up by name and will fail silently on a typo.

- [ ] **Step 3: Add the `Detail` boolean property**

```js
const base = await figma.getNodeByIdAsync(BASE_ID);
const propId = base.addComponentProperty("ShowDetail", "BOOLEAN", false);
const detail = base.findChild(n => n.name === "Detail");
detail.componentPropertyReferences = { visible: propId };
return JSON.stringify({ propId: propId, defs: Object.keys(base.componentPropertyDefinitions) });
```

Expected: `defs` contains a key beginning with `ShowDetail`.

- [ ] **Step 4: Screenshot and eyeball**

`get_screenshot` on the base component id. Confirm: four bands, correct proportions, detail band hidden, 2px dark border, 14px radius.

- [ ] **Step 5: Commit**

No repo files change in this task. Record the base component's node id in `card-constants.json` under `"baseComponentId"` and commit that.

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/card-constants.json
git commit -m "Record Node/_Base component id"
```

---

### Task 4: Build the `Note` component set

**Files:**
- Modify: `Components v2` page in Figma
- Modify: `skills/figma-arch-diagram/references/card-constants.json` (add `noteSetId`)

**Interfaces:**
- Consumes: `card-constants.json` (`W`, `PAD`).
- Produces: a `COMPONENT_SET` named `Note` with variant property `Kind` and values `warn`, `broken`, `ok`. Each variant has children named `Icon` (ELLIPSE) and `Body` (TEXT). Phase 2's emitter instantiates this and calls `setProperties({ Kind: "warn" })`.

Colours, matching the existing `Data Tracking` board convention:

| Kind | Fill | Stroke | Icon circle | Glyph |
|---|---|---|---|---|
| `warn` | `#FDF6DD` | `#E7D9A0` | `#C9A227` | `!` |
| `broken` | `#FDECEB` | `#F0C3BF` | `#C0392B` | `×` |
| `ok` | `#EAF7EE` | `#B9E0C6` | `#2E8B57` | `✓` |

- [ ] **Step 1: Create the three variants**

```js
const C = /* card-constants.json */;
const page = await figma.getNodeByIdAsync(PAGE_ID);
const FONT = { family: "Nunito", style: "SemiBold Italic" };
await figma.loadFontAsync(FONT);

const KINDS = [
  { k: "warn",   bg: [0.992,0.965,0.867], st: [0.906,0.851,0.627], ic: [0.788,0.635,0.153], g: "!" },
  { k: "broken", bg: [0.992,0.925,0.922], st: [0.941,0.765,0.749], ic: [0.753,0.224,0.169], g: "×" },
  { k: "ok",     bg: [0.918,0.969,0.933], st: [0.725,0.878,0.776], ic: [0.180,0.545,0.341], g: "✓" }
];
const solid = (c) => [{ type: "SOLID", color: { r: c[0], g: c[1], b: c[2] } }];
const made = [];

for (let i = 0; i < KINDS.length; i++) {
  const K = KINDS[i];
  const v = figma.createComponent();
  v.name = `Kind=${K.k}`;
  v.resize(C.W, 84);
  v.cornerRadius = 10;
  v.fills = solid(K.bg);
  v.strokes = solid(K.st);
  v.strokeWeight = 1;
  page.appendChild(v);
  v.x = 400; v.y = i * 100;

  const dot = figma.createEllipse();
  dot.name = "Icon";
  v.appendChild(dot);
  dot.resize(16, 16);
  dot.x = 10; dot.y = 10;
  dot.fills = solid(K.ic);

  const glyph = figma.createText();
  glyph.fontName = FONT; glyph.name = "Glyph"; glyph.fontSize = 11;
  glyph.characters = K.g;
  glyph.fills = [{ type: "SOLID", color: { r: 1, g: 1, b: 1 } }];
  v.appendChild(glyph);
  glyph.x = 10 + (16 - glyph.width) / 2;
  glyph.y = 10 + (16 - glyph.height) / 2;

  const body = figma.createText();
  body.fontName = FONT; body.name = "Body"; body.fontSize = 12;
  body.characters = "Note text";
  body.textAutoResize = "HEIGHT";
  v.appendChild(body);
  body.resize(C.W - 34 - 10, 20);
  body.x = 34; body.y = 10;
  body.fills = solid([0.36,0.325,0.251]);

  made.push(v.id);
}
return JSON.stringify({ ids: made });
```

- [ ] **Step 2: Combine into a variant set**

```js
const nodes = [];
for (const id of IDS) nodes.push(await figma.getNodeByIdAsync(id));
const set = figma.combineAsVariants(nodes, await figma.getNodeByIdAsync(PAGE_ID));
set.name = "Note";
return JSON.stringify({ id: set.id, type: set.type,
                        props: set.componentPropertyDefinitions,
                        variants: set.children.map(c => c.name) });
```

Expected: `type` === `"COMPONENT_SET"`, `props` has key `Kind` with `variantOptions` `["warn","broken","ok"]`, `variants.length` === 3.

- [ ] **Step 3: Screenshot and eyeball**

`get_screenshot` on the set id. Confirm three colour-coded notes, glyph centred in its circle, body text not overflowing the card.

- [ ] **Step 4: Record the set id and commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/card-constants.json
git commit -m "Add Note component set with warn/broken/ok variants"
```

---

### Task 5: Batch-rebuild all 117 brand components

The bulk transform. Runs in **batches of one category set per `use_figma` call**, not all 117 at once. Batching keeps each call's runtime bounded and, critically, avoids the known stale-node-reference failure that occurs when many freshly-cloned nodes are mutated in a single call.

> **Structural note (fill in from Task 1 Step 4):** `Node/*` container type came back as `COMPONENT_SET`. All 13 sets already have a `Brand` variant property. Skip any `combineAsVariants` step for existing sets; that call is only needed for the *new* v2 sets this task builds from scratch (Step 4 below), which is unrelated to the original structural question.

**Files:**
- Modify: `Components v2` page in Figma
- Modify: `skills/figma-arch-diagram/references/library-inventory.json` (add `v2Id` per brand)

**Interfaces:**
- Consumes: `library-inventory.json` (Task 1), `card-constants.json` incl. `baseComponentId` (Tasks 2–3).
- Produces: 13 component sets on `Components v2`, same names and same `Brand` variant values as the originals, every component `C.W` × (`C.H_COMPACT` or `C.H_EXTENDED`). Each brand entry in the inventory gains `"v2Id"`.

Per-brand transform rules:

1. Clone `Node/_Base`, rename to the original's `Brand=X` name.
2. `Title.characters` = the brand's display name, taken from the original's **last** label if it had one label, or its **first** label if it had two (the GTM exemplar already puts the title first). Preserve any manual `\n` in the original characters.
   - **One exception.** `Brand=Customer Journey Analytics` is the only brand in the library whose title wraps to 3 lines and would clip against `TITLE_H` (2 lines). Set its `Title.characters` to `"Customer Journey\nAnalytics"`: at fontSize 15 across the 104-wide text block that fits in two lines. Task 1 verified the distribution is 102 one-line, 15 two-line, and this single three-line case, so no other brand needs special handling. Do not raise `TITLE_H` to accommodate one card.
3. Copy the original's icon frame (by `icon.iconLayerName`) into the base's `icon` frame, and rescale it by **`min(1, ICON_H / b.icon.h)`, the brand's own recorded height**, not by a shape-class constant. Per-brand scaling is correct for the outliers the inventory found (Rust's 73.5-tall chrome, the three `Node/Client` device silhouettes at 78/75/84.1) which a shape-class constant would distort. `icon.shape` is descriptive metadata only and must not drive geometry. The icon band is auto-layout centred, so no manual positioning is needed.
4. `Id.characters` = the original's second label if it had two (e.g. `GTM-123456`), else a placeholder sample for that category (table below).
5. `Detail` stays hidden; `ShowDetail` defaults false.

Sample `Id` values are **per-brand, not per-category**: they live in `skills/figma-arch-diagram/references/brand-samples.json`, keyed by set name then brand name. Each one matches the identifier format that brand actually uses (`G-ABC1234567` for GA4, `acct_1A2b3C4d` for Stripe, `s3://bucket` for S3), so the card documents the expected shape of the value rather than a generic stand-in. The file is verified to cover all 117 brands with no gaps and no orphans.

Look the value up as `SAMPLES[setName][brand]`. If a brand is somehow missing from the map, **stop and report** rather than substituting a generic default, since a silent fallback would reintroduce exactly the genericness this file exists to remove.

- [ ] **Step 1: Transform the smallest set first as a canary**

Start with `Node/Messaging` (`308:571`, 2 brands). Load `figma-use`, then:

```js
const C = /* card-constants.json */;
const INV = /* the one set's brands array from library-inventory.json */;
const SET_NAME = "Node/Messaging";
const SAMPLES = /* the SET_NAME sub-object from brand-samples.json */;
const page = await figma.getNodeByIdAsync(PAGE_ID);
const base = await figma.getNodeByIdAsync(C.baseComponentId);
const FONT = { family: "Nunito", style: "SemiBold Italic" };
await figma.loadFontAsync(FONT);

const out = [];
for (const b of INV) {
  const card = base.clone();
  card.name = b.name;
  page.appendChild(card);

  const orig = await figma.getNodeByIdAsync(b.id);
  // Icon layer names are NOT uniform: Node/Server's 5 brands use "Rack", not "icon".
  // Task 1 recorded the real name per brand as b.icon.iconLayerName; always use it.
  const origIcon = orig.findChild(n => n.name === b.icon.iconLayerName).clone();
  const scale = Math.min(1, C.ICON_H / b.icon.h);
  if (scale < 1) origIcon.rescale(scale);
  const slot = card.findChild(n => n.name === "icon");
  slot.appendChild(origIcon);   // slot is auto-layout + centred; no manual x/y needed

  const titleSrc = b.labels.length === 2 ? b.labels[0] : b.labels[b.labels.length - 1];
  card.findChild(n => n.name === "Title").characters = titleSrc.chars;
  const sample = SAMPLES[b.brand];
  if (!sample) throw new Error("No brand-samples.json entry for " + SET_NAME + "::" + b.brand);
  card.findChild(n => n.name === "Id").characters =
    b.labels.length === 2 ? b.labels[1].chars : sample;

  out.push({ brand: b.brand, v2Id: card.id, w: card.width, h: card.height });
}
return JSON.stringify(out);
```

- [ ] **Step 2: Assert the canary**

Expected from Step 1's return: 2 entries, every `w` === 140, every `h` === `C.H_COMPACT`. Screenshot both cards with `get_screenshot` and confirm the icon is centred, the title reads correctly, and the sample id is present.

**If the canary is wrong, fix the script before touching the other 12 sets.** This is the whole point of running it first.

- [ ] **Step 3: Run the remaining 12 sets, one call each**

In this order (smallest first, so failures surface cheaply): `Business & Ops` (2), `Client` (3), `Security & CDN` (4), `API & Services` (5), `Server` (5), `Content & Marketing` (7), `Observability` (9), `Data Store` (11), `DevOps` (13), `Language` (17), `Framework` (18), `Adobe Experience Cloud` (21).

Same script, swapping `INV` and `SAMPLE_ID`. After each call, assert the returned count matches the expected brand count for that category and that every `h` is `H_COMPACT`.

`Data Store` and `Server` are the cylinder categories, so expect `scale < 1` there if `ICON_H < 112.5`.

- [ ] **Step 4: Combine each category into a variant set**

For each of the 13 categories:

```js
const nodes = [];
for (const id of V2_IDS_FOR_CATEGORY) nodes.push(await figma.getNodeByIdAsync(id));
const set = figma.combineAsVariants(nodes, await figma.getNodeByIdAsync(PAGE_ID));
set.name = CATEGORY_NAME;   // e.g. "Node/Messaging"
return JSON.stringify({ id: set.id, type: set.type,
                        props: set.componentPropertyDefinitions,
                        count: set.children.length });
```

Assert per category: `type` === `"COMPONENT_SET"`, `props` has a `Brand` key, `count` matches the expected brand count.

- [ ] **Step 5: Update the inventory with v2 ids**

Write `v2Id` and the new set ids back into `library-inventory.json`.

- [ ] **Step 6: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/library-inventory.json
git commit -m "Rebuild all 117 brand components as normalized four-band cards"
```

---

### Task 6: Verify, document, and hand over

**Files:**
- Create: `skills/figma-arch-diagram/references/library-map.md`

**Interfaces:**
- Consumes: `library-inventory.json` with `v2Id`s.
- Produces: `library-map.md`, the human- and agent-readable category → set-id map Phase 2's skill loads to resolve a brand name to a component set.

- [ ] **Step 1: Run the full-library assertion**

```js
const page = await figma.getNodeByIdAsync(PAGE_ID);
const sets = page.children.filter(n => n.type === "COMPONENT_SET" && n.name.startsWith("Node/"));
const heights = new Set(), widths = new Set();
let total = 0, badProps = [];
for (const s of sets) {
  if (!s.componentPropertyDefinitions.Brand) badProps.push(s.name);
  for (const v of s.children) { total++; heights.add(v.height); widths.add(v.width); }
}
return JSON.stringify({ setCount: sets.length, total: total,
                        widths: [...widths], heights: [...heights], badProps: badProps });
```

Expected exactly:
- `setCount` === 13
- `total` === 117
- `widths` === `[140]`
- `heights` === `[H_COMPACT]`: **a single value.** More than one means a card escaped normalization; find it and fix it before proceeding.
- `badProps` === `[]`

- [ ] **Step 2: Render a full-page proof sheet**

`get_screenshot` on the `Components v2` page with `maxDimension: 2400`. Download and view. Confirm: every card the same height, titles legible and correctly split across two lines, icons vertically centred and consistently sized within each shape family, sample ids present.

- [ ] **Step 3: Get Sam's sign-off**

Show the proof sheet. Ask via AskUserQuestion (`multiSelect: true`) whether to promote v2. **This is the gate: do not rename any page without an explicit yes.**

- [ ] **Step 4: On approval, promote v2**

```js
const legacy = await figma.getNodeByIdAsync("0:1");
legacy.name = "Components (legacy — pre-normalization)";
const v2 = await figma.getNodeByIdAsync(PAGE_ID);
v2.name = "Components";
return JSON.stringify({ legacy: legacy.name, current: v2.name });
```

Rollback if anything is wrong later: rename back and delete the v2 page. The originals were never mutated.

- [ ] **Step 5: Write `library-map.md`**

A table per category (set name, set node id, `Brand` variant values), generated from `library-inventory.json`. Head it with the file key, the page name, and the capture date so staleness is detectable.

- [ ] **Step 6: Commit**

```bash
cd ~/Development/diagramming
git add skills/figma-arch-diagram/references/library-map.md
git commit -m "Add library map and promote normalized components"
```

---

## Done when

- `Components v2` is promoted to `Components`, the originals preserved on a legacy page.
- All 117 components are 140 wide and share one height.
- `Note` exists as a `COMPONENT_SET` with `Kind` = warn / broken / ok.
- `library-inventory.json`, `card-constants.json`, and `library-map.md` are committed.
- Phase 2's plan can be written against real, measured constants.

## Not in this plan

- The `figma-arch-diagram` skill, spec format, layout engine, emitter, and verification pass: Phase 2, planned separately once `card-constants.json` exists.
- Migrating diagrams already drawn on canvas.
- The `Database` / `Service` / `ServiceHorizontal` / `Queue` / `IconUserIcon` primitives: they are not brand cards and are left as-is until Phase 2 shows whether the layout engine needs them.
