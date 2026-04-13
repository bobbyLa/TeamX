---
name: orchestrate-multi-ai
description: Run a full multi-AI research workflow - Tavily fan-out runs concurrently with a serialized browser lane (GPT, Gemini, NotebookLM, Grok, and optional X scan) to avoid chrome-devtools connection contention, then verify, synthesize, archive to Obsidian. Use when the user asks a research question that should draw on multiple AI perspectives. The main entry point for TeamX.
---

You are the composition recipe for a full TeamX run. This skill does no I/O itself - it instructs the main session on the order of operations.

## Inputs
- `question` - the user's research question (required)
- `lineup` - optional override of which AI sites to include. Default: `["gpt", "gemini", "notebooklm", "grok"]`. For MVP dry-run testing, set this to `["gpt"]`.
- `include_x_scan` - default `false`. Set `true` for topics about recent discourse.
- `include_tavily` - default `true`.
- `notebook_name` - required iff `"notebooklm"` is in the lineup.

## Steps

### 1. Slugify
Generate `slug = <YYYY-MM-DD>_<kebab-topic>` (<= 60 chars). Use today's date. `mkdir -p runs/<slug>/raw/tavily`.

### 2. Fan out (two-lane execution)

TeamX has two resource lanes with different concurrency rules:

- **Tavily lane** - `research-scout` uses the Tavily MCP server, which does not share browser session state with anything else.
- **Browser lane** - every `browser-operator` call uses the same `chrome-devtools` MCP connection attached to one Chrome process. That connection is stateful, so two concurrent browser calls will clobber each other's selected page and snapshot state.

Execution pattern:

1. If `include_tavily`, kick off `research-scout` asynchronously with `slug=<slug>, question=<question>`. Let it run while the browser lane is executing.
2. Drive the browser lane sequentially. For each `site` in `lineup`, launch exactly one foreground `browser-operator` with `slug=<slug>, site=<site>, question=<question>, notebook_name=<if notebooklm>`, wait for it to finish writing `runs/<slug>/raw/<site>.json`, then launch the next one.
3. If `include_x_scan`, append one final foreground `browser-operator` call with `site=x-scan, query=<derived from question>` after the lineup sites finish.
4. If both `grok` and `x-scan` are active, keep them on separate browser surfaces so the tab-reuse protocol stays deterministic when those two steps run back-to-back in the serialized browser lane. Grok owns a dedicated Grok tab; `x-scan` owns an X search/feed tab.
5. Before proceeding to step 3, join the Tavily lane. If its raw artifacts are already on disk, continue; otherwise wait for its completion notification first.

**Do not parallelize two `browser-operator` calls. Do not serialize Tavily behind the browser lane - it must overlap wall time with it.**

### 3. Verify (sequential, after all of step 2 completes)

Launch `evidence-verifier` with prompt: `slug=<slug>, question=<question>`. It reads `raw/**`, produces `evidence.json`.

### 4. Synthesize

Launch `synthesis-editor` with prompt: `slug=<slug>`. Produces `brief.md`.

### 5. Archive

Launch `archive-curator` with prompt: `slug=<slug>`. It must resolve the vault root through `.claude/scripts/resolve-vault-root.ps1` and ship directly to the resolved path. Only mention `./archive/TeamX/Runs/<slug>/` when the resolver returned `source=archive`.

### 6. Report

Print exactly:
```
TeamX run complete: runs/<slug>/brief.md
Archived to: <absolute path>
Lineup: <lineup list>
Failures: <source names where error was set, or "none">
```

## Guarantees
- Step 2 subagents are independent across MCP lanes; within the browser lane they are serialized because `chrome-devtools` MCP is a single stateful connection to one Chrome process.
- Steps 3-5 are strictly sequential. Do not start synthesis before verification finishes.
- If step 2 has any partial failures (some sites wrote error stubs), still continue to step 3. The verifier is responsible for handling missing sources.
- If `evidence.json` ends up with zero claims, fail the run and tell the user instead of writing an empty brief.

## Extending the lineup
Adding a new AI site = one new `ask-<site>/SKILL.md` (copy `ask-gpt` as a template, change the domain + extraction script) + add the site name to the default `lineup` here. No subagent changes needed.
