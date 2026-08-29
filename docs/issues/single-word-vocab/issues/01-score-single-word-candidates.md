# Score single-word candidates in the vocab miner

Status: ready-for-agent

## Problem

`mine-vocab.mjs` only builds 2-grams and 3-grams (`phrasesFrom` defaults to `min: 2, max: 3`), so a domain term that is one word can never reach the shortlist.

Found while dogfooding the miner on this repo: "dogfood" appears in four separate typed turns across multiple sessions and never ranked. So do plenty of other single-word domain nouns in other repos ("bucket", "promoted", "harness"). The user has to notice the gap themselves and add the term by hand, which is the work the miner exists to remove.

## Why it was built this way

The floor of 2 is deliberate, not an oversight. Single words are overwhelmingly noise: the stopword list that makes 2-grams usable is nowhere near strict enough for 1-grams, where every ordinary English noun in a sentence becomes a candidate. Simply lowering `min` to 1 would bury the real terms.

## Proposed approach

Score 1-grams, but behind a much higher bar than multi-word phrases:

- Require a higher session spread than the current `count >= 2` floor, so a word has to recur across several separate sessions.
- Require `inCode`, so the word is one the codebase itself writes down. A single word that only ever appears in chat is almost always ordinary English.
- Keep them out of the containment-pruning pass, or a 1-gram will be swallowed by every phrase that contains it.

## Acceptance

- A tests-first slice at the ranking seam: a fixture where a single word recurs across sessions and appears in `codeText` surfaces it, and one where it appears in only one session, or not in the code, does not.
- Running the miner against this repo surfaces "dogfood" without the top of the shortlist filling with ordinary English.
- `npm test` green.

## Context

Shipped in v2.0.2. See `.agents/adr/0007-setup-seeds-the-glossary-from-past-sessions.md` for why the miner exists and `docs/plans/2026-08-29-mine-user-vocab-in-setup.md` for the design record, whose ranking section this would extend.
