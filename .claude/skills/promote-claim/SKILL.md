---
name: promote-claim
description: Turn a single verified claim from a research run's evidence.json into an atomic evergreen note under TeamX/Knowledge/. Only invoked by knowledge-curator on explicit user request - never automatically.
---

## Inputs (from parent agent)

- `slug` - the run slug, e.g. `2026-04-13_moe-architectures`.
- `claim_id` - the `id` field of the target claim inside `runs/<slug>/evidence.json`.
- `topic` (optional) - override the default topic-folder inference.

## Preconditions

- `runs/<slug>/evidence.json` exists and contains a claim matching `claim_id`.
- `runs/<slug>/brief.md` exists (used for context extraction).
- Resolve `OBSIDIAN_VAULT` in this order: env var, then `./.env`, then `./archive/` with an explicit warning.

## Procedure

1. Read `runs/<slug>/evidence.json`. Find the claim where `id == <claim_id>`. If not found, fail with `error: claim <id> not in evidence.json`.
2. Read `runs/<slug>/brief.md`. Search for 2-4 sentences of surrounding context that mention the claim's key nouns. Extract verbatim.
3. Derive `topic`:
   - If the user supplied one, use it.
   - Else read `evidence.json`'s `question` and the brief's `tags` frontmatter and pick a short kebab slug (one word is fine). Example: `moe`, `us-iran`, `quantization`.
4. Resolve the vault root in this order: `$OBSIDIAN_VAULT`, then `./.env`, else `./archive/` with an explicit warning in the final message.
5. Target file: `<vault>/TeamX/Knowledge/<topic>/<slug>-<claim_id>.md`.
6. If the target exists, read it. If its frontmatter `source_claim_id` matches, this is a re-promotion - allowed, overwrite the body but preserve any `## 相关` links the user added. If `source_claim_id` differs, abort with a clear error.
7. If the target does not exist, create parent dirs.
8. Write the file following `.claude/rules/output-contract.md` section 5 exactly. Fill in:
   - `title` - claim rewritten as a short phrase (max 12 words).
   - `type: knowledge-atom`
   - `tags: [teamx, <topic>]` plus any tags the brief's frontmatter had.
   - `source_run` - wikilink to the brief: `"[[Runs/<slug>/brief]]"`.
   - `source_claim_id` - the claim id.
   - `confidence` - copy from the claim.
   - `created` - today's date.
   - Body: blockquote of the claim's verbatim text, the context you extracted, then the sources list from `claim.sources` rendered as follows:
     - If the source string contains no `:`, render `- [[Runs/<slug>/raw/<source>.json|<source>]]`.
     - If the source string contains `:`, split on the first `:` into `<label>` and `<value>`.
     - If `<value>` already starts with `http://` or `https://`, render `- [<label>] <value>`.
     - Else if `<value>` is a domain/path you can reliably normalize, render `- [<label>] https://<value>`.
     - Else render `- <original source string>` as plain text rather than inventing a link.
   - `## 相关` - grep the existing Knowledge folder for notes whose frontmatter `tags` overlap with this one; include up to 5 wikilinks. If none, leave the section with a single `- (none)` line.
9. After writing the atom, run `python .claude/scripts/sync-knowledge-links.py --path "<absolute atom path>"`.
10. After link sync succeeds, call `refresh-indexes` so `Index/knowledge.base` picks up the new atom.

## Scope discipline

- Only write under `<vault>/TeamX/Knowledge/**`.
- Never modify source files under `runs/` or the brief's frontmatter.
- Never create an atom from a claim with `confidence: low` unless the user explicitly asked - warn first.

## Final message

`promoted <slug>/<claim_id> -> <absolute path>` plus `refreshed links and indexes`. If fallback was used, append `(OBSIDIAN_VAULT missing in env and .env - used ./archive/)`.
