# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

TeamX is a Claude Code "second brain" team. The main session orchestrates specialized subagents that drive external AI sites (ChatGPT, Gemini, NotebookLM, Grok) and X through **chrome-devtools MCP** on an already-logged-in Chrome, run web research through **Tavily MCP**, and sediment the results into an Obsidian vault via filesystem MCP. The vault is the long-term memory: research runs, daily work logs, atomic knowledge notes, and queryable Bases views all live there.

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
   │    ├─ archive-curator                     writes TeamX/Runs/<slug>/ (briefs + evidence)
   │    ├─ journal-curator                     writes TeamX/Daily/<date>.md (session logs)
   │    └─ knowledge-curator                   writes TeamX/Knowledge/** + TeamX/Index/**
   │
   ├─ Skills                               →  .claude/skills/*/SKILL.md
   │    ├─ ask-gpt / ask-gemini                site-specific playbooks
   │    │  ask-notebooklm / ask-grok
   │    ├─ scan-x                              X post harvester
   │    ├─ tavily-search / extract / crawl     thin Tavily wrappers
   │    ├─ build-evidence-pack                 deterministic merger
   │    ├─ archive-to-obsidian                 vault writer (Runs/ lane)
   │    ├─ log-day                             daily-log appender (Daily/ lane)
   │    ├─ promote-claim                       claim → knowledge atom (Knowledge/ lane)
   │    ├─ refresh-indexes                     regenerates Index/*.base files
   │    ├─ obsidian-markdown / obsidian-cli    OFM syntax + CLI helpers (foundations)
   │    ├─ obsidian-bases / json-canvas        database views + visual maps
   │    ├─ defuddle                            web-page → clean markdown (for future Knowledge/)
   │    └─ orchestrate-multi-ai                composition recipe
   │
   ├─ MCP                                  →  .mcp.json
   │    ├─ chrome-devtools   (attaches to running Chrome via --browserUrl)
   │    ├─ tavily            (remote HTTP MCP; authenticate once via /mcp)
   │    ├─ filesystem        (scoped to OBSIDIAN_VAULT or ./archive/)
   │    └─ github            (stdio MCP; reads GITHUB_PERSONAL_ACCESS_TOKEN from .env)
   │
   └─ Hooks                                →  .claude/settings.json + .claude/hooks/
        ├─ PreToolUse         pre-write-guard.sh — refuses writes outside runs/, archive/, .claude/logs/, $OBSIDIAN_VAULT and validates TeamX vault note schemas
        ├─ PostToolUse        log-tool-call.sh — appends JSONL to .claude/logs/trace-<date>.jsonl
        └─ SubagentStop       same log-tool-call.sh with "subagent-stop" marker

Per-run artifacts                          →  runs/<slug>/
   ├─ raw/<source>.json / raw/tavily/*     per-source artifacts
   ├─ evidence.json                        normalized claims + contradictions
   ├─ brief.md                             final memo
   └─ trace.jsonl                          audit log

Long-term memory (Obsidian vault)          →  $OBSIDIAN_VAULT/TeamX/
   ├─ Runs/<slug>/                         archived briefs + evidence (archive-curator)
   │    ├─ brief.md / evidence.json
   │    ├─ raw/                           archived source artifacts linked from the brief
   │    ├─ assets/                        screenshots, generated images
   │    └─ sources/                       PDFs, original documents
   ├─ Daily/<YYYY-MM-DD>.md                session logs, one file/day (journal-curator)
   ├─ News/inbox.md                       breaking news quick-capture
   ├─ Knowledge/<topic>/<atom>.md          promoted claim atoms (knowledge-curator)
   ├─ Prompts/                            reusable prompt templates (research/analysis/synthesis/sites/)
   ├─ Resources/                           cross-run shared materials and images
   ├─ Index/                               runs.base / knowledge.base / daily.base
   └─ Maps/<topic>.canvas                  optional visual relationship maps
```

| Primitive              | Path                                        |
| ---------------------- | ------------------------------------------- |
| Orchestrator rules     | `CLAUDE.md` (this file), `.claude/rules/*`  |
| Vault path rules       | `.claude/rules/vault-path-resolution.md`    |
| Subagents              | `.claude/agents/<name>.md`                  |
| Skills                 | `.claude/skills/<name>/SKILL.md`            |
| MCP servers            | `.mcp.json`                                 |
| Hooks config           | `.claude/settings.json`                     |
| Hook scripts           | `.claude/hooks/*.sh`                        |
| Vault config mirror    | `.obsidian-config/**`                       |
| Per-run artifacts      | `runs/<slug>/` (gitignored)                 |
| Vault — runs           | `$OBSIDIAN_VAULT/TeamX/Runs/<slug>/`        |
| Vault — daily logs     | `$OBSIDIAN_VAULT/TeamX/Daily/<date>.md`     |
| Vault — knowledge      | `$OBSIDIAN_VAULT/TeamX/Knowledge/<topic>/*` |
| Vault — indexes        | `$OBSIDIAN_VAULT/TeamX/Index/*.base`        |
| Vault — news           | `$OBSIDIAN_VAULT/TeamX/News/inbox.md`       |
| Vault — prompts        | `$OBSIDIAN_VAULT/TeamX/Prompts/**`          |
| Vault — resources      | `$OBSIDIAN_VAULT/TeamX/Resources/**`        |

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

The orchestrator skill generates a slug, starts the Tavily lane asynchronously, walks the browser lane one `browser-operator` at a time, joins Tavily, runs the verifier → synthesis-editor → archive-curator pipeline, and prints the path to `brief.md`.

For a quick dry run while you're still validating selectors, override the lineup:
```
/orchestrate-multi-ai "<question>" lineup=["gpt"]
```

### 4. Other vault operations

- **Log today's session**: run `/log-day` at the end of a working session. The `journal-curator` subagent will append a structured block to `$OBSIDIAN_VAULT/TeamX/Daily/<today>.md`. Never runs automatically — if you don't invoke it, no daily log gets written.
- **Promote a claim into a knowledge atom**: ask the main session to "promote `c03` from `<slug>`". The `knowledge-curator` subagent will create a new atom under `Knowledge/<topic>/<slug>-c03.md` with full source-run backlinks, then refresh the `Index/knowledge.base` view.
- **Rebuild the database views**: ask "refresh indexes". The `knowledge-curator` will regenerate `runs.base`, `knowledge.base`, and `daily.base` under `Index/`.
- **Capture breaking news**: open `News/inbox.md` in Obsidian and write a few lines. When ready for deep research, run `/orchestrate-multi-ai` and archive to `Runs/`.

### 5. Where to look for results

- `runs/<slug>/brief.md` — the fresh human-readable output of a research run
- `runs/<slug>/evidence.json` — the claim graph
- `runs/<slug>/raw/*.json` — per-source artifacts (useful for debugging a flaky site)
- `$OBSIDIAN_VAULT/TeamX/Runs/<slug>/` — archived copy of the run
- `$OBSIDIAN_VAULT/TeamX/Daily/<date>.md` — session logs
- `$OBSIDIAN_VAULT/TeamX/News/inbox.md` — breaking news capture
- `$OBSIDIAN_VAULT/TeamX/Knowledge/<topic>/*.md` — promoted evergreen notes
- `$OBSIDIAN_VAULT/TeamX/Prompts/**` — accumulated prompt templates
- `$OBSIDIAN_VAULT/TeamX/Resources/**` — shared images and documents
- `$OBSIDIAN_VAULT/TeamX/Index/*.base` — Obsidian Bases database views
- `.claude/logs/trace-<date>.jsonl` — hook-written audit trail (also the source for `/log-day`)
- `.obsidian-config/**` — versioned snapshot of the vault's portable Obsidian configuration (`scripts/sync-vault-config.ps1`)

## Team conventions

- **Files, not messages, are the team's protocol.** Subagents communicate by writing into `runs/<slug>/` or the vault. Never return long prose as a subagent tool result — write the file and report `wrote <path>`.
- **Every `ask-*` skill writes its artifact even on failure.** A missing raw file is a bug; a raw file with `error.stage` set is normal. The verifier is designed to handle partial failures gracefully.
- **Three curators, three lanes into `$OBSIDIAN_VAULT`:**
  - `archive-curator` owns `TeamX/Runs/**` (research run archives).
  - `journal-curator` owns `TeamX/Daily/**` (session logs, append-only).
  - `knowledge-curator` owns `TeamX/Knowledge/**` and `TeamX/Index/**` (atoms + Bases views).
  No other subagent touches the vault. No curator writes outside its own lane. This is enforced by convention inside each curator's prompt and by the pre-write-guard hook at the vault-path level.
- **Knowledge promotion is always explicit.** `archive-curator` never auto-promotes claims. The only way something lands in `Knowledge/` is a direct user instruction like "promote `c03` from `<slug>`". This keeps the atom library signal-dense.
- **Daily logs are manual.** `/log-day` is the only trigger. There is no Stop-hook automation; if you forget to run it, that day has no log. This is intentional — the cost of automated pollution of the vault is higher than the cost of occasional missed days.
- **News capture is manual.** Open `News/inbox.md` and write when something catches your attention. Deep research triggers an `/orchestrate-multi-ai` run separately.
- **Prompt templates live in the vault.** Write effective prompts into `Prompts/**` (tagged `type: prompt-template`) so they can be searched and iterated on in Obsidian. Verified improvements sync back to `.claude/skills/ask-*/SKILL.md`.
- **All vault path decisions go through the shared resolver.** Before any write into `TeamX/**`, call `.claude/scripts/resolve-vault-root.ps1 -RepoRoot <repo-root> -OnMissing archive|error`. An empty shell `$OBSIDIAN_VAULT` is not enough to declare the vault unconfigured - the resolver must check `.env` first.
- **Ad-hoc draft notes follow the same rule.** Even temporary `type: draft` notes under `TeamX/Knowledge/**` must write directly to the resolved vault path when the resolver returns `source=env` or `source=dotenv`. Do not stage them under `archive/` and migrate later.
- **Adding a new AI site is strictly local:** copy `ask-gpt/SKILL.md` to `ask-<new-site>/SKILL.md`, change the domain and the extraction snippet, add the site name to `orchestrate-multi-ai/SKILL.md`'s default lineup. No subagent changes.
- **Parallelism is non-negotiable across MCP lanes in step 2 of `orchestrate-multi-ai`.** Tavily (`research-scout`) must overlap wall time with the browser lane. Within the browser lane, `browser-operator` calls are serialized because `chrome-devtools` MCP is a single stateful connection to one Chrome process - parallel calls clobber each other's selected page. Never sequentialize the whole fan-out; never parallelize two `browser-operator` calls.
- **Selectors come from `take_snapshot` at runtime**, not from hardcoded CSS. If a site's a11y tree changes, upgrade that one `ask-*` skill.
- **Output contract is authoritative.** If a skill's output doesn't match `.claude/rules/output-contract.md`, fix the skill, not the contract.

## Environment variables

Read from `.env` at the project root (gitignored). Template is in `.env.example`.

| Var                  | What for                                                  |
| -------------------- | --------------------------------------------------------- |
| `OBSIDIAN_VAULT`     | absolute path to the vault root; all three curators write under `<vault>/TeamX/{Runs,Daily,Knowledge,Index}/`. If unset, the project falls back to `./archive/TeamX/...` |
| `CHROME_DEBUG_URL`   | chrome-devtools MCP `--browserUrl` target; default `http://127.0.0.1:9333` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP credential loaded by `.claude/scripts/start-github-mcp.ps1`; create it with `repo`, `read:user`, and `read:org` scopes |

All production vault-path resolution must go through `.claude/scripts/resolve-vault-root.ps1`; do not treat an empty process env var as proof that `OBSIDIAN_VAULT` is unset.

## Security fences

The `PreToolUse` hook (`.claude/hooks/pre-write-guard.sh`) blocks `Write` and `Edit` to anywhere except:
- `runs/**`
- `archive/**`
- `.claude/logs/**`
- `.claude/plans/**`
- `.claude/projects/*/memory/**`
- `$OBSIDIAN_VAULT/**`

This means a subagent cannot rewrite `.mcp.json`, `CLAUDE.md`, or any skill definition during a research run. To intentionally modify the architecture, do it from a plain interactive session where you'll be aware of the writes, and set `TEAMX_UNLOCK=1` in the environment (or use the Write-to-`.claude/logs/_stage/` + `mv` pattern).

The `PostToolUse` hook logs every tool call (tool name + truncated input) to `.claude/logs/trace-<date>.jsonl`, which doubles as a chain-of-custody for the evidence pack and the raw source for `/log-day`.
