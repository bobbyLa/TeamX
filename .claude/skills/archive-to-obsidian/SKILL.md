---
name: archive-to-obsidian
description: Copy a completed run (brief.md + evidence.json) into the Obsidian vault under TeamX/<slug>/. Use inside archive-curator as the final step of orchestrate-multi-ai. Falls back to ./archive/ if OBSIDIAN_VAULT is unset.
---

## Inputs
- `slug`

## Preconditions
- `runs/<slug>/brief.md` exists and is readable.
- `runs/<slug>/evidence.json` exists.
- `OBSIDIAN_VAULT` env var is set to an absolute path. If not, use `./archive/` and warn in the final summary.

## Procedure

1. Resolve the target directory:
   - If `$OBSIDIAN_VAULT` is non-empty → `<vault>/TeamX/<slug>/`.
   - Else → `./archive/TeamX/<slug>/`.
2. `Read runs/<slug>/brief.md`.
3. Parse its frontmatter. Ensure `tags` array contains `teamx`. If not, inject it (before writing to the vault, not in the source file).
4. Write `<target>/brief.md` with the adjusted frontmatter + original body.
5. `Read runs/<slug>/evidence.json` and write it verbatim to `<target>/evidence.json`.
6. Write `<target>/README.md` — one paragraph:
   ```markdown
   # <title from frontmatter>
   Run: `<slug>`
   Source: `runs/<slug>/` (in the TeamX project)
   Created: `<created>`
   ```
7. Final message: `archived to <absolute target path>`. If fallback was used, also say: `(OBSIDIAN_VAULT not set — used ./archive/)`.

## Scope discipline
- Never modify `runs/<slug>/*`.
- Never write outside the resolved target dir.
- If `<target>/brief.md` already exists, read it first; if the frontmatter `slug` matches, overwrite; otherwise abort with a clear error.
