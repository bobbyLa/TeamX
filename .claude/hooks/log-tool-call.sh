#!/usr/bin/env bash
# Append one JSONL line per tool call to .claude/logs/trace-<date>.jsonl.
set -eu

logdir=".claude/logs"
mkdir -p "$logdir"
logfile="$logdir/trace-$(date +%F).jsonl"

payload=$(cat 2>/dev/null || true)
marker="${1:-tool}"

ts=$(date -u +%FT%TZ)
# Truncate payload to keep the log small.
snippet=$(printf '%s' "$payload" | tr -d '\n' | cut -c1-400)
printf '{"ts":"%s","kind":"%s","snippet":%s}\n' \
  "$ts" "$marker" "$(printf '%s' "$snippet" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "\"%s\"", $0}')" \
  >> "$logfile"
