---
name: orchestrate-multi-ai
description: Run a full multi-AI research workflow — fan out to GPT/Gemini/NotebookLM/Grok + Tavily in parallel, verify, synthesize, archive to Obsidian. Use when the user asks a research question that should draw on multiple AI perspectives. The main entry point for TeamX.
---

You are the composition recipe for a full TeamX run. This skill does no I/O itself — it instructs the main session on the order of operations.

## Inputs
- `question` — the user's research question (required)
- `lineup` — optional override of which AI sites to include. Default: `["gpt", "gemini", "notebooklm", "grok"]`. For MVP dry-run testing, set this to `["gpt"]`.
- `include_x_scan` — default `false`. Set `true` for topics about recent discourse.
- `include_tavily` — default `true`.
- `notebook_name` — required iff `"notebooklm"` is in the lineup.

## Steps

### 1. Slugify
Generate `slug = <YYYY-MM-DD>_<kebab-topic>` (≤40 chars). Use today's date. `mkdir -p runs/<slug>/raw/tavily`.

### 2. Fan out (parallel — ONE message, multiple Agent calls)

In a single assistant message, launch these subagents in parallel:

- For each `site` in `lineup`: launch `browser-operator` with prompt: `slug=<slug>, site=<site>, question=<question>, notebook_name=<if notebooklm>`. Each browser-operator invocation targets one site only.
- If `include_tavily`: launch `research-scout` with `slug=<slug>, question=<question>`.
- If `include_x_scan`: launch a second `browser-operator` with `site=x-scan, query=<derived from question>`.

**Do not sequentialize step 2.** Step 2 is the whole point of having subagents.

### 3. Verify (sequential, after all of step 2 completes)

Launch `evidence-verifier` with prompt: `slug=<slug>, question=<question>`. It reads `raw/**`, produces `evidence.json`.

### 4. Synthesize

Launch `synthesis-editor` with prompt: `slug=<slug>`. Produces `brief.md`.

### 5. Archive

Launch `archive-curator` with prompt: `slug=<slug>`. Ships to `$OBSIDIAN_VAULT/TeamX/<slug>/` or `./archive/TeamX/<slug>/`.

### 6. Report

Print exactly:
```
TeamX run complete: runs/<slug>/brief.md
Archived to: <absolute path>
Lineup: <lineup list>
Failures: <source names where error was set, or "none">
```

## Guarantees
- Step 2 subagents are independent — no one reads another's output mid-run.
- Steps 3–5 are strictly sequential. Do not start synthesis before verification finishes.
- If step 2 has any partial failures (some sites wrote error stubs), still continue to step 3. The verifier is responsible for handling missing sources.
- If `evidence.json` ends up with zero claims, fail the run and tell the user instead of writing an empty brief.

## Extending the lineup
Adding a new AI site = one new `ask-<site>/SKILL.md` (copy `ask-gpt` as a template, change the domain + extraction script) + add the site name to the default `lineup` here. No subagent changes needed.
