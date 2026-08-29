# Diagram spec format

The authoring contract for `figma-arch-diagram`. Author a plain JS/JSON object (the "raw" spec), pass it to `normalizeSpec(raw)` from `scripts/spec.mjs`, and pass the *normalized* result on to `layout` and the emitter. Defaults are applied and the spec is validated exactly once, inside `normalizeSpec`. Nothing downstream should re-apply a default or re-check a reference: if `normalizeSpec` returned, the spec is already complete and internally consistent.

`normalizeSpec` never mutates its input; it returns a new object tree.

## Top-level shape

```js
{
  title: string,
  direction: "LR" | "TB",
  rows: [ /* Row */ ],
  edges: [ /* Edge, cross-row only */ ],
  annotations: [ /* Annotation */ ]
}
```

- `title`: required, non-empty. No default; omitting it throws.
- `direction`: layout direction for the whole board. Defaults to `"LR"` (left-to-right) if absent. `"TB"` (top-to-bottom) is the only other accepted value.
- `rows`: the diagram's rows, each laid out as its own horizontal (or vertical, under `TB`) band. Defaults to `[]` if absent.
- `edges`: **cross-row** connections only. See "Row edges vs. cross-row edges" below. Defaults to `[]` if absent.
- `annotations`: board-level callouts not attached to any single node (e.g. a summary note in a corner). Defaults to `[]` if absent.

## Row shape

```js
{
  id: string,
  title: string,
  nodes: [ /* Node */ ],
  edges: [ /* Edge, within this row only */ ],
  notes: [ /* Note */ ]
}
```

- `id`: required, non-empty. Used as the row's own identifier (not a node id); later tasks use it to key layout bands.
- `title`: the row's caption, e.g. a subsystem or environment name. Defaults to `""` if absent.
- `nodes`: the component cards in this row. Defaults to `[]` if absent.
- `edges`: connections between two nodes that both live in this row. Defaults to `[]` if absent.
- `notes`: annotations attached to a specific node in this row. Defaults to `[]` if absent.

## Node shape

```js
{
  id: string, category: string, brand: string,
  title: string, instance: string,
  detail: string,
  lane: "main" | "sub"
}
```

- `id`: required, non-empty, and unique across the **entire spec** (not just within the row, since node ids form one global namespace so that edges and notes can reference any node regardless of which row it lives in).
- `category`: required, non-empty. Must match a category key in `component-keys.json` (e.g. `"Node/Framework"`) so the emitter can resolve a publishable component.
- `brand`: required, non-empty. Must match a brand variant under that category in `component-keys.json` (e.g. `"Next.js"` under `"Node/Framework"`).
- `title`: required, non-empty. The card's display label (shown regardless of `category`/`brand`).
- `instance`: required, non-empty. The card's identifying detail line: an environment name, a container ID, a tracking ID, etc.
- `detail`: free-text elaboration shown in the card's expanded detail band. Defaults to `""` if absent. Limited to 4 lines (split on `\n`); a 5th line throws.
- `lane`: `"main"` places the node on the row's primary line; `"sub"` places it on a secondary line beneath, for nodes that branch off a main-lane node rather than continuing the primary flow. Defaults to `"main"` if absent.

## Row edges vs. cross-row edges

Every edge has the shape:

```js
{ from: string, to: string, label: string }
```

- `from` / `to`: required, must each be the `id` of a node that exists somewhere in the spec.
- `label`: optional caption drawn on the connector. Defaults to `""` if absent.

`row.edges` and top-level `spec.edges` share this exact shape, but scope differs:

- **`row.edges`** connect two nodes that both live in the *same* row. Use this for the normal, linear flow within one subsystem.
- **`spec.edges`** (top level) connect nodes in *different* rows. Use this when one row's node feeds a node that lives in another row, for example a page in a "site" row that also feeds a node in a separate "call tracking" row. There is no way to express a cross-row relationship inside a single row's `edges`; it must go at the top level.

Both are validated against the same global node-id set built while normalizing `rows`, so a `from`/`to` typo is caught the same way in either place, and nothing stops you from writing a same-row edge at the top level; the type distinction is purely by convention/organization, not enforced by which row a node lives in.

## Notes

Attached to one node, drawn near that card:

```js
{ on: string, kind: "warn" | "broken" | "ok", text: string }
```

- `on`: required, the `id` of a node that exists somewhere in the spec.
- `kind`: required, one of `"warn"`, `"broken"`, `"ok"`. Any other value throws.
- `text`: the note's body text. Defaults to `""` if absent.

## Annotations

Board-level callouts, not attached to any node:

```js
{ kind: "warn" | "broken" | "ok", title: string, text: string }
```

- `kind`: required, one of `"warn"`, `"broken"`, `"ok"`. Any other value throws.
- `title`: defaults to `""` if absent.
- `text`: defaults to `""` if absent.

## Validation errors

`normalizeSpec` throws a plain `Error` (never returns a partial spec) on any of the following, in this order. Node-level checks run first because reference checks below depend on the fully-populated node-id set:

| Condition | Message |
|---|---|
| `raw` is missing, `null`, or not an object | `spec must be an object` |
| `raw.title` is missing or empty | `spec.title is required` |
| `raw.direction` is set and isn't `"LR"` or `"TB"` | `direction must be LR or TB` |
| a row has no `id` | `every row needs an id` |
| a node is missing `id`, `category`, `brand`, `title`, or `instance` | `node.<field> is required (node <id or ?>)` |
| a node id repeats anywhere in the spec | `duplicate node id: <id>` |
| a node's `detail` has more than 4 lines | `detail exceeds 4 lines (node <id>)` |
| a node's `lane` is set and isn't `"main"` or `"sub"` | `lane must be main or sub (node <id>)` |
| a row or top-level edge's `from` doesn't match any node id | `edge source not found: <id>` |
| a row or top-level edge's `to` doesn't match any node id | `edge target not found: <id>` |
| a note's `on` doesn't match any node id | `note target not found: <id>` |
| a note's `kind` isn't `"warn"`, `"broken"`, or `"ok"` | `note kind must be warn, broken or ok` |
| an annotation's `kind` isn't `"warn"`, `"broken"`, or `"ok"` | `annotation kind must be warn, broken or ok` |

## Worked example

A production tracking pipeline: a site page loads a data-layer script, which feeds Google Tag Manager, which fires a Google tag, which forwards to GA4 and, on a separate sub-lane, to Google Ads.

```js
const raw = {
  title: 'Marketing site tracking pipeline',
  direction: 'LR',
  rows: [
    {
      id: 'tracking',
      title: 'SHIPPED: Production since v4.21.10',
      nodes: [
        { id: 'mktg-site', category: 'Node/Framework', brand: 'Next.js', title: 'MKTG Site', instance: 'Production' },
        { id: 'data-layer', category: 'Node/Language', brand: 'JavaScript', title: 'window.dataLayer', instance: 'ad_phone_click' },
        { id: 'gtm', category: 'Node/Content & Marketing', brand: 'Google Tag Manager', title: 'Google Tag Manager', instance: 'GTM-5KJTHP3M' },
        { id: 'google-tag', category: 'Node/Content & Marketing', brand: 'Google Tag', title: 'Google tag', instance: 'AW-794559089' },
        { id: 'ga4', category: 'Node/Content & Marketing', brand: 'Google Analytics 4', title: 'GA4', instance: 'G-SRHWP4RYKP' },
        { id: 'google-ads', category: 'Node/Content & Marketing', brand: 'Google Ads', title: 'Google Ads', instance: '626-214-8456', lane: 'sub' }
      ],
      edges: [
        { from: 'mktg-site', to: 'data-layer', label: 'page load' },
        { from: 'data-layer', to: 'gtm', label: 'push' },
        { from: 'gtm', to: 'google-tag' },
        { from: 'google-tag', to: 'ga4' },
        { from: 'google-tag', to: 'google-ads' }
      ],
      notes: [
        { on: 'gtm', kind: 'warn', text: 'NO phone numbers in container' }
      ]
    }
  ],
  annotations: [
    { kind: 'ok', title: 'Tracking verified', text: 'All conversion events firing correctly as of last audit.' }
  ]
}

const spec = normalizeSpec(raw)
```

Every `category`/`brand` pair above is taken verbatim from `component-keys.json`; the emitter looks up the component key by that exact pair, so a mismatched string (e.g. `"Google Analytics"` instead of `"Google Analytics 4"`) fails to resolve a component even though `normalizeSpec` itself has no opinion on which brands exist; it only checks that the fields are non-empty strings.

To see a cross-row edge (a node in one row feeding a node in another), add a second row and connect them at the top level instead of inside either row's `edges`:

```js
edges: [
  { from: 'mktg-site', to: 'call-tracking-node', label: 'referrer' }
]
```

where `call-tracking-node` is the id of a node declared in a different row's `nodes` list.
