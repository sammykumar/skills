---
"sk-skills": minor
---

New `figma-arch-diagram` skill: build or update an architecture, tech-stack, networking, or data-flow diagram on a FigJam board from the published "Icon Lib - Editable" component library. Nothing on the board is placed by hand. The diagram is authored as a spec, a pure layout engine (38 unit tests, no Figma) solves every coordinate, cards are placed by component key rather than node id, and connectors bind to explicit magnets so Figma never re-routes a line through a text label. It closes by verifying the result, both by assertion and by looking at the rendered board, since text overflow and connector routes are invisible to the Plugin API.

It is the one skill in the set that does not run everywhere: the cards come from a specific published Figma library, so without access to that library no card can be placed.
