# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

TeamX is a Claude Code "second brain" team. The main session orchestrates specialized subagents that drive external AI sites (ChatGPT, Gemini, NotebookLM, Grok) and X through **chrome-devtools MCP** on an already-logged-in Chrome, run web research through **Tavily MCP**, and archive curated briefs into an Obsidian vault via filesystem MCP.

This is not an application codebase — there's no build or test pipeline. The "source code" is the set of skill playbooks, subagent definitions, and MCP wiring under `.claude/` and `.mcp.json`. Changes are evaluated by running an end-to-end TeamX workflow, not by unit tests.

## Architecture

```
User Task
   │
   ▼
Lead / Orchestrator (Claude Code main session)
   │
   ├─ Task Router                          →  CLAUDE.md + orchestrate-multi-ai skill
   │    ├─ site selection
   │    ├─ source priority
   │    └─ output contract                 →  .claude/rules/output-contract.md
   │
   ├─ Subagents                            →  .claude/agents/*.md
   │    ├─ browser-operator                    drives chrome-devtools MCP (one site/call)
   │    ├─ research-scout                      drives Tavily MCP (parallel fan-out)
   │    ├─ evidence-verifier                   reads raw/, writes evidence.json
   │    ├─ synthesis-editor                    reads evidence.json, writes brief.md
   │    └─ archive-curator                     copies brief + evidence into Obsidian
   │
   ├─ Skills                               →  .claude/skills/*/SKILL.md
   │    ├─ ask-gpt / ask-gemini                site-specific playbooks
   │    │  ask-notebooklm / ask-grok
   │    ├─ scan-x                              X post harvester
   │    ├─ tavily-search / extract / crawl     thin Tavily wrappers
   │    ├─ build-evidence-pack                 deterministic merger
   │    ├─ archive-to-obsidian                 vault writer
   │    └─ orchestrate-multi-ai                composition recipe
   │
   ├─ MCP                                  →  .mcp.json
   │    ├─ chrome-devtools   (attaches to running Chrome via --browserUrl)
   │    ├─ tavily            (remote HTTP MCP; authenticate once via /mcp)
   │    ├─ filesystem        (scoped to OBSIDIAN_VAULT or ./archive/)
   │    └─ github            (stdio MCP; reads GITHUB_PERSONAL_ACCESS_TOKEN from .env)
   │
   └─ Hooks                                →  .claude/settings.json + .claude/hooks/
        ├─ PreToolUse         pre-write-guard.sh — refuses writes outside runs/, archive/, .claude/logs/, $OBSIDIAN_VAULT
        ├─ PostToolUse        log-tool-call.sh — appends JSONL to .claude/logs/trace-<date>.jsonl
        └─ SubagentStop       same log-tool-call.sh with "subagent-stop" marker

Outputs                                    →  runs/<slug>/
   ├─ raw/<source>.json / raw/tavily/*     per-source artifacts
   ├─ evidence.json                        normalized claims + contradictions
   ├─ brief.md                             final memo
   └─ trace.jsonl                          audit log
```

| Primitive              | Path                                        |
| ---------------------- | ------------------------------------------- |
| Orchestrator rules     | `CLAUDE.md` (this file), `.claude/rules/*`  |
| Subagents              | `.claude/agents/<name>.md`                  |
| Skills                 | `.claude/skills/<name>/SKILL.md`            |
| MCP servers            | `.mcp.json`                                 |
| Hooks config           | `.claude/settings.json`                     |
| Hook scripts           | `.claude/hooks/*.sh`                        |
| Per-run artifacts      | `runs/<slug>/` (gitignored)                 |
| Archived briefs        | `$OBSIDIAN_VAULT/TeamX/<slug>/`             |

## Running it

### 1. One-time setup

Copy the env template and fill in the machine-specific paths/endpoints:
```bash
cp .env.example .env
# Edit .env and set OBSIDIAN_VAULT, CHROME_DEBUG_URL, GITHUB_PERSONAL_ACCESS_TOKEN
```

Launch Chrome once with the remote debugging port and a dedicated profile. On first launch, **log into ChatGPT, Gemini, NotebookLM, Grok, and X manually** — those cookies persist in `.chrome-profile/` for subsequent runs.
```bash
# Windows
.\.claude\scripts\start-chrome-devtools.ps1
```
This project uses an imported copy of the system `Default` profile inside `.chrome-profile/`, so TeamX does not depend on your day-to-day Chrome instance. After the first import, TeamX reuses only the project-local profile. If your system login state changes, run `.\.claude\scripts\start-chrome-devtools.ps1 -ForceResync`.
When Claude boots `chrome-devtools` MCP from `.mcp.json`, it now runs the same startup logic automatically, so opening Claude is enough to ensure the dedicated browser is available.

If you need to launch it manually instead of using the helper script:
```bash
# Windows
chrome.exe --remote-debugging-port=9333 --user-data-dir="E:/Team2/TeamX/.chrome-profile" --profile-directory=Default
```
Keep this Chrome window open whenever TeamX is running. It's the long-lived browser that chrome-devtools MCP attaches to.

Authenticate Tavily once from inside Claude Code:
```
/mcp
```
Choose `tavily` and complete the OAuth flow in your browser. This project now uses Tavily's remote HTTP MCP, so no API key is required in `.env` or `.mcp.json`.

### 2. Verify MCP wiring

From inside `E:/Team2/TeamX`, start Claude Code, then:
```
/mcp
```
All four servers (`chrome-devtools`, `tavily`, `filesystem`, `github`) must show connected. If `chrome-devtools` fails, check that Chrome is running with `--remote-debugging-port=9333` and that `CHROME_DEBUG_URL` in `.env` matches. If `tavily` is disconnected, open `/mcp` and authenticate it. If `github` is disconnected, check that `GITHUB_PERSONAL_ACCESS_TOKEN` is set in `.env`.

### 3. Kick off a run

```
/orchestrate-multi-ai "What are recent developments in MoE architectures?"
```

The orchestrator skill generates a slug, fans out to the lineup **in parallel**, waits for all raw/ files, runs the verifier → synthesis-editor → archive-curator pipeline, and prints the path to `brief.md`.

For a quick dry run while you're still validating selectors, override the lineup:
```
/orchestrate-multi-ai "<question>" lineup=["gpt"]
```

### 4. Where to look for results
- `runs/<slug>/brief.md` — the human-readable output
- `runs/<slug>/evidence.json` — the claim graph
- `runs/<slug>/raw/*.json` — per-source artifacts (useful for debugging a flaky site)
- `$OBSIDIAN_VAULT/TeamX/<slug>/` — archived copy
- `.claude/logs/trace-<date>.jsonl` — hook-written audit trail

## Team conventions

- **Files, not messages, are the team's protocol.** Subagents communicate by writing into `runs/<slug>/`. Never return long prose as a subagent tool result — write the file and report `wrote <path>`.
- **Every `ask-*` skill writes its artifact even on failure.** A missing raw file is a bug; a raw file with `error.stage` set is normal. The verifier is designed to handle partial failures gracefully.
- **`archive-curator` is the only writer into `$OBSIDIAN_VAULT`.** Nothing else touches the vault, ever. This is enforced by convention (the other subagents don't have Write in the vault path) and by the pre-write-guard hook.
- **Adding a new AI site is strictly local:** copy `ask-gpt/SKILL.md` to `ask-<new-site>/SKILL.md`, change the domain and the extraction snippet, add the site name to `orchestrate-multi-ai/SKILL.md`'s default lineup. No subagent changes.
- **Parallelism is non-negotiable in step 2 of `orchestrate-multi-ai`.** Fan-out must be a single assistant message with multiple Agent tool calls. Sequentializing defeats the architecture.
- **Selectors come from `take_snapshot` at runtime**, not from hardcoded CSS. If a site's a11y tree changes, upgrade that one `ask-*` skill.
- **Output contract is authoritative.** If a skill's output doesn't match `.claude/rules/output-contract.md`, fix the skill, not the contract.

## Environment variables

Read from `.env` at the project root (gitignored). Template is in `.env.example`.

| Var                  | What for                                                  |
| -------------------- | --------------------------------------------------------- |
| `OBSIDIAN_VAULT`     | absolute path to the vault root; archive-curator writes under `<vault>/TeamX/<slug>/`. If unset, falls back to `./archive/` |
| `CHROME_DEBUG_URL`   | chrome-devtools MCP `--browserUrl` target; default `http://127.0.0.1:9333` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP credential loaded by `.claude/scripts/start-github-mcp.ps1`; create it with `repo`, `read:user`, and `read:org` scopes |

## Security fences

The `PreToolUse` hook (`.claude/hooks/pre-write-guard.sh`) blocks `Write` and `Edit` to anywhere except:
- `runs/**`
- `archive/**`
- `.claude/logs/**`
- `$OBSIDIAN_VAULT/**`

This means a subagent cannot rewrite `.mcp.json`, `CLAUDE.md`, or any skill definition during a research run. To intentionally modify the architecture, do it from a plain interactive session where you'll be aware of the writes.

The `PostToolUse` hook logs every tool call (tool name + truncated input) to `.claude/logs/trace-<date>.jsonl`, which doubles as a chain-of-custody for the evidence pack.
