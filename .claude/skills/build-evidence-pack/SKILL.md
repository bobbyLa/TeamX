---
name: build-evidence-pack
description: Deterministic merger that reads all raw artifacts in a run and produces evidence.json following the output contract. Use inside evidence-verifier, or from the main session when the verifier subagent is unavailable.
---

You turn `runs/<slug>/raw/**` into `runs/<slug>/evidence.json`.

## Procedure

1. `Glob runs/<slug>/raw/**/*.json` → list of raw files.
2. For each file, `Read` it and:
   - Skip files with `error` set but remember them for `open_questions`.
   - Tavily files: treat each `result.results[]` item as a source; pull title/URL/snippet.
   - `ask-*` files: treat `answer_md` as the source text; keep `source` as the citation key.
3. Extract **atomic claims** from the collected text. Rules:
   - One factual assertion per claim.
   - Rewrite to remove "I think" / "it seems" hedging — if a source hedged, lower its confidence.
   - Do not include opinions, pleasantries, or meta-commentary about the question itself.
4. Merge identical claims across sources into a single entry; populate `sources[]` with every contributing source name.
5. Assign confidence per `.claude/rules/output-contract.md` § 2:
   - `high` — ≥2 independent sources agree.
   - `medium` — 1 authoritative source (arxiv / nature / official docs / gov).
   - `low` — 1 AI-site assertion without external backing.
6. Detect contradictions: two claims that reference the same subject with incompatible predicates. Create both claims, then add a `contradictions[]` entry listing their IDs and one sentence describing the disagreement.
7. Gather `open_questions` from: sources that errored out, claims nobody addressed but the user's question implied, explicit "I don't know" from any AI site.
8. Write `runs/<slug>/evidence.json` with `slug`, `question`, `created` (UTC now), `claims`, `contradictions`, `open_questions`.

## Scope discipline
- Never edit `raw/` files.
- Never write anything except `runs/<slug>/evidence.json`.
- No free-form prose output; the file is the product.
