#!/usr/bin/env bash
# Refuse writes outside the team's allowed directories during a research run.
# Escape hatch: set TEAMX_UNLOCK=1 in the environment for architecture maintenance.
set -eu

if [ "${TEAMX_UNLOCK:-}" = "1" ]; then
  exit 0
fi

# Claude Code's process env does not carry values from .env (MCP startup scripts
# read that file independently). Load OBSIDIAN_VAULT here so curator writes into
# the vault are actually allowed at runtime.
if [ -z "${OBSIDIAN_VAULT:-}" ]; then
  for envfile in ".env" "${CLAUDE_PROJECT_DIR:-}/.env" "E:/Team2/TeamX/.env"; do
    [ -z "$envfile" ] && continue
    [ -f "$envfile" ] || continue
    val=$(grep -E '^OBSIDIAN_VAULT=' "$envfile" 2>/dev/null | head -1 | sed -E 's/^OBSIDIAN_VAULT=//' | tr -d '\r\n')
    if [ -n "$val" ]; then
      OBSIDIAN_VAULT="$val"
      break
    fi
  done
fi

payload=$(cat)
path=$(printf '%s' "$payload" | grep -oE '"file_path"[^"]*"[^"]+"' | head -1 | sed -E 's/.*"file_path"[^"]*"([^"]+)".*/\1/')

[ -z "$path" ] && exit 0

# Replace every backslash with /, then collapse multiple slashes.
norm=$(printf '%s' "$path" | tr '\\' '/' | sed 's|//*|/|g')
rel=$(printf '%s' "$norm" | sed -E 's|^[A-Za-z]:/Team2/TeamX/||')
allowed=0

case "$rel" in
  runs/*|archive/*|.claude/logs/*) allowed=1 ;;
esac

case "$norm" in
  */.claude/projects/*/memory/*) allowed=1 ;;
  */.claude/plans/*) allowed=1 ;;
esac

vault="${OBSIDIAN_VAULT:-}"
if [ -n "$vault" ]; then
  vn=$(printf '%s' "$vault" | tr '\\' '/' | sed 's|//*|/|g')
  case "$norm" in "$vn"/*|"$vn") allowed=1 ;; esac
fi

if [ "$allowed" -ne 1 ]; then
  echo "pre-write-guard: refusing write to '$path' (normalized: '$norm')." >&2
  echo "  Allowed: runs/, archive/, .claude/logs/, \$OBSIDIAN_VAULT, auto-memory, plans." >&2
  echo "  For architecture edits, re-run with TEAMX_UNLOCK=1 in the environment." >&2
  exit 2
fi

schema_script=".claude/hooks/pre-write-schema.py"
if [ -f "$schema_script" ]; then
  if command -v python3 >/dev/null 2>&1; then
    py="python3"
  elif command -v python >/dev/null 2>&1; then
    py="python"
  elif [ -f ".venv/Scripts/python.exe" ]; then
    py=".venv/Scripts/python.exe"
  elif [ -f ".venv/Scripts/python" ]; then
    py=".venv/Scripts/python"
  else
    echo "pre-write-guard: warning - no Python interpreter found; skipped schema validation." >&2
    exit 0
  fi

  printf '%s' "$payload" | "$py" "$schema_script"
fi

exit 0
