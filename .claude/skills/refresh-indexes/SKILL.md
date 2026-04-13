---
name: refresh-indexes
description: Regenerate the TeamX/Index/*.base files (Obsidian Bases views) over the current Runs/, Knowledge/, and Daily/ folders. Idempotent - derives entirely from frontmatter, never reads user-authored body text.
---

## What you produce

Three `.base` files under `<vault>/TeamX/Index/`:

1. `runs.base` - table of all research runs, sorted by `created` descending.
2. `knowledge.base` - card view of all knowledge atoms, grouped by `tags`.
3. `daily.base` - timeline view of daily notes, sorted by `date` descending.

Each `.base` file is pure YAML. Obsidian Bases reads frontmatter properties from the source `.md` files at render time - you do not need to scan the notes' content, only list the filter/columns configuration.

## Procedure

1. Resolve the vault root by calling `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/scripts/resolve-vault-root.ps1 -RepoRoot <repo-root> -OnMissing archive`.
   - Parse the JSON result and use `<root>` as the vault root.
   - Only treat `source=archive` / `usedFallback=true` as a real fallback.
   - If `source=env` or `source=dotenv`, write directly to that vault path and do not claim the vault is unset.
2. Ensure `<vault>/TeamX/Index/` exists.
3. Write `runs.base` with this body (literal, safe to overwrite):
   ```yaml
   filters:
     and:
       - file.path.startsWith("TeamX/Runs/")
       - file.name == "brief"
   views:
     - type: table
       name: All research runs
       order:
         - file.name
         - title
         - created
         - tags
         - sources
       sort:
         - property: created
           direction: DESC
   ```
4. Write `knowledge.base` with this body:
   ```yaml
   filters:
     and:
       - file.path.startsWith("TeamX/Knowledge/")
       - type == "knowledge-atom"
   views:
     - type: cards
       name: Knowledge atoms
       order:
         - title
         - tags
         - source_run
         - confidence
         - created
       sort:
         - property: created
           direction: DESC
   ```
5. Write `daily.base` with this body:
   ```yaml
   filters:
     and:
       - file.path.startsWith("TeamX/Daily/")
       - tags.contains("daily")
   views:
     - type: table
       name: Daily timeline
       order:
         - file.name
         - date
         - runs
       sort:
         - property: date
           direction: DESC
   ```
6. Always overwrite the three files wholesale - they are derived artifacts, never hand-edited. If the user hand-edits them, tell them in the final message that their edits were discarded.

## Scope discipline

- Only ever write under `<vault>/TeamX/Index/`.
- Never touch `Runs/`, `Knowledge/`, or `Daily/`.
- Never read note bodies - frontmatter properties are enough, Obsidian Bases does the rest at render time.

## Final message

`refreshed runs.base / knowledge.base / daily.base at <absolute index path>`. Append the fallback warning only when the resolver returned `source=archive`.
