---
name: log-day
description: Append a structured session block to today's daily note in the Obsidian vault. Used by journal-curator when the user invokes /log-day. Never overwrites prior session blocks.
---

## Inputs (from parent agent)

- `topic` - short session title, one line.
- `summary_bullets` - 3-5 bullets of what got done.
- `decisions` - 0-3 bullets (optional).
- `artifacts` - wikilinks to runs/knowledge/plans (optional).
- `open_threads` - 0-3 bullets (optional).
- `linked_runs` - list of slugs referenced this session (optional).
- `session_id` - the current Claude session id (optional but preferred).

If any of these are missing, best-effort infer from `.claude/logs/trace-<today>.jsonl` (the PostToolUse tail for today). Resolve `session_id` first (use the provided one, else extract the newest `"session_id":"..."` from today's trace), then read only the last ~200 lines whose `snippet` contains that session id.

## Procedure

1. Compute `<date>` = today in `YYYY-MM-DD` local time.
2. Compute `<hhmm>` = current local time in `HH:MM`.
3. Resolve target path:
   - Call `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/scripts/resolve-vault-root.ps1 -RepoRoot <repo-root> -OnMissing archive`
   - Parse the JSON result and use `<root>/TeamX/Daily/<date>.md`
   - Only treat `source=archive` / `usedFallback=true` as a real fallback
   - If `source=env` or `source=dotenv`, write directly to that vault path and do not say the vault is unset
4. Resolve `session_id`: use the provided value if present; else extract the newest `"session_id":"..."` from today's trace lines.
5. If any structured inputs are missing, filter today's trace to lines whose `snippet` contains `"session_id":"<session_id>"`, then summarize the last ~200 matching lines only.
6. Check if the target exists.
7. If not, create parent dirs and write the full daily file:
   ```markdown
   ---
   date: <date>
   tags: [teamx, daily]
   runs: [<wikilinks to linked_runs, or empty>]
   ---

   # <date>

   ## <hhmm> - <topic>
   - **做了什么**:
     - <summary_bullets[0]>
     - <summary_bullets[1]>
     - ...
   - **关键决策/学到的**:
     - <decisions[0]>
     - ...
   - **产物**:
     - <artifacts[0]>
     - ...
   - **未决/待续**:
     - <open_threads[0]>
     - ...
   ```
   Omit any sub-bullet list whose source array is empty.
8. If it already exists, read it. Append only a new `## <hhmm> - <topic>` block at the end with the same structure. Additionally, merge `linked_runs` wikilinks into the frontmatter `runs:` array (deduplicate). This is the only frontmatter mutation allowed.
9. Write via the filesystem MCP under the resolved `TeamX/Daily/` path. If obsidian-cli is available and the user's Obsidian instance is running, prefer the CLI path so Obsidian reloads the file without a disk poll; otherwise fall back to direct filesystem write.

## Scope discipline

- Only write to `TeamX/Daily/<date>.md`. Never another path.
- Never delete or reorder prior session blocks.
- If the file grew past 200KB, warn in the final message but still append.
- The frontmatter `date:` field must equal the file's date - never re-date an existing file.

## Final message

`appended session block to <absolute path>` - or `created <absolute path>` if this was a new day. Append the fallback warning only when the resolver returned `source=archive`.
