# Vault Path Resolution

All writes into `TeamX/**` inside the Obsidian vault must resolve the vault root through `.claude/scripts/resolve-vault-root.ps1`.

## Resolution Contract

- Call `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/scripts/resolve-vault-root.ps1 -RepoRoot <repo-root> -OnMissing archive|error`.
- Parse the single-line JSON response: `{"root":"<abs path>","source":"env|dotenv|archive","usedFallback":true|false}`.
- Resolution order is fixed: process env first, then repo `.env`, then `./archive/` only when `-OnMissing archive` is used.
- If `OBSIDIAN_VAULT` exists in env or `.env` but points to a missing or non-directory path, hard-fail. Do not silently fall back to `./archive/`.

## Required Behavior

- An empty shell `$OBSIDIAN_VAULT` does not mean the vault is unconfigured. `.env` must be checked through the resolver before any fallback message is shown.
- If the resolver returns `source=env` or `source=dotenv`, write directly to that real vault path. Do not stage into `archive/` and migrate later.
- If the resolver returns `source=archive`, fallback is active and must be called out explicitly in the final user-facing message.
- This applies to curator lanes and to ad-hoc draft notes such as `type: draft` files under `TeamX/Knowledge/**`.

## Message Rules

- `source=env` or `source=dotenv`: report only the real destination path.
- `source=archive`: report the destination path and state that fallback was used because `OBSIDIAN_VAULT` was missing in both env and `.env`.
- If a temporary migration ever happens for recovery, the message must say it was migrated and cleaned up. Do not present the intermediate `archive/` path as the final outcome.
