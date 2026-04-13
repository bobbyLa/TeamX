---
name: archive-to-obsidian
description: Copy a completed run (brief.md + evidence.json) into the Obsidian vault under TeamX/Runs/<slug>/. Use inside archive-curator as the final step of orchestrate-multi-ai. Falls back to ./archive/ if OBSIDIAN_VAULT is unset.
---

## Inputs
- `slug`

## Preconditions
- `runs/<slug>/brief.md` exists and is readable.
- `runs/<slug>/evidence.json` exists.
- Resolve the vault root only through `.claude/scripts/resolve-vault-root.ps1`. An empty shell `$OBSIDIAN_VAULT` is not enough to declare the vault unconfigured.

## Procedure

1. Resolve the target directory:
   - Call `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/scripts/resolve-vault-root.ps1 -RepoRoot <repo-root> -OnMissing archive`.
   - Parse the JSON result and use `<root>/TeamX/Runs/<slug>/`.
   - Only treat `source=archive` / `usedFallback=true` as a real fallback.
   - If `source=env` or `source=dotenv`, write directly to that vault path and do not claim `OBSIDIAN_VAULT` is unset.
2. Read `runs/<slug>/brief.md`.
3. Parse its frontmatter. Ensure `tags` array contains `teamx`. If not, inject it (before writing to the vault, not in the source file).
4. Write `<target>/brief.md` with the adjusted frontmatter + original body.
5. Read `runs/<slug>/evidence.json` and write it verbatim to `<target>/evidence.json`.
6. Write `<target>/README.md` with one short paragraph:
   ```markdown
   # <title from frontmatter>
   Run: `<slug>`
   Source: `runs/<slug>/` (in the TeamX project)
   Created: `<created>`
   ```
7. Run `python .claude/scripts/archive-run-assets.py --source-root "runs/<slug>" --target-root "<target>"`.
   - The helper copies any run-local files referenced by `brief.md` into the archived run, preserving subpaths like `raw/`, `assets/`, and `sources/`.
   - It also rewrites the archived `brief.md` so local links now point at the copied files instead of the project-local `runs/<slug>/...` path.
8. Final message: `archived to <absolute target path>`. If the helper migrated files, include a short count. Append the fallback warning only when the resolver returned `source=archive`.

## Scope discipline
- Never modify `runs/<slug>/*`.
- Never write outside the resolved target dir.
- Never write into `Daily/`, `Knowledge/`, or `Index/` - those are owned by `journal-curator` and `knowledge-curator`.
- If `<target>/brief.md` already exists, read it first; if the frontmatter `slug` matches, overwrite; otherwise abort with a clear error.
