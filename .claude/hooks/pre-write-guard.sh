#!/usr/bin/env bash
# Refuse writes outside the team's allowed directories during a research run.
# Escape hatch: set TEAMX_UNLOCK=1 in the environment for architecture maintenance.
set -eu

if [ "${TEAMX_UNLOCK:-}" = "1" ]; then
  exit 0
fi

payload=$(cat)
path=$(printf '%s' "$payload" | grep -oE '"file_path"[^"]*"[^"]+"' | head -1 | sed -E 's/.*"file_path"[^"]*"([^"]+)".*/\1/')

[ -z "$path" ] && exit 0

# Replace every backslash with /, then collapse multiple slashes.
norm=$(printf '%s' "$path" | tr '\\' '/' | sed 's|//*|/|g')
rel=$(printf '%s' "$norm" | sed -E 's|^[A-Za-z]:/Team2/TeamX/||')

case "$rel" in
  runs/*|archive/*|.claude/logs/*) exit 0 ;;
esac

case "$norm" in
  */.claude/projects/*/memory/*) exit 0 ;;
  */.claude/plans/*) exit 0 ;;
esac

vault="${OBSIDIAN_VAULT:-}"
if [ -n "$vault" ]; then
  vn=$(printf '%s' "$vault" | tr '\\' '/' | sed 's|//*|/|g')
  case "$norm" in "$vn"/*|"$vn") exit 0 ;; esac
fi

echo "pre-write-guard: refusing write to '$path' (normalized: '$norm')." >&2
echo "  Allowed: runs/, archive/, .claude/logs/, \$OBSIDIAN_VAULT, auto-memory, plans." >&2
echo "  For architecture edits, re-run with TEAMX_UNLOCK=1 in the environment." >&2
exit 2
