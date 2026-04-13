---
name: ask-grok
description: Ask a question to Grok via the already-logged-in grok.com (or x.com) session. Use when orchestrate-multi-ai's lineup includes Grok. Grok's strength is X-post grounding, so prefer it for questions about recent events and online discourse.
---

You are driving the browser-operator subagent to get a Grok answer.

## Inputs
- `slug`, `question`

## Preconditions
- Logged in to `grok.com` or `x.com` with Grok access enabled.
- Think mode is OFF for MVP.

## Playbook

1. `list_pages` first. Reuse an existing `grok.com` tab if one exists. If none exists, `new_page` to `https://grok.com/`, even if unrelated `x.com` tabs are already open.
2. If the selected `grok.com` tab is on the wrong subpage, recover inside that same tab with `navigate_page` to `https://grok.com/`. Only if `grok.com` is unavailable should you fall back inside that same dedicated tab to `https://x.com/i/grok`.
3. Never commandeer a general `x.com` tab for Grok. `scan-x` owns the `x.com/search` surface in the browser lane; keep Grok on `grok.com` (fallback `x.com/i/grok`) so the two steps never fight over tab state.
4. `take_snapshot`. Find the composer `textbox`. On grok.com it is usually labeled "Ask anything" or similar.
5. Build the envelope from `site-prompting.md` and append the trailing line `Avoid speculation beyond what X posts support.` per the Grok deviation rule.
6. `fill` the composer, `click` send (or Enter).
7. `wait_for` the response to complete. Timeout 120s.
8. `evaluate_script` to extract the last assistant turn and any cited X posts. Grok often renders post cards inline; capture their URLs into `citations[]`.
9. Write `runs/<slug>/raw/grok.json`.

## Failure modes
- Think mode auto-enabled: disable and retry once; if it re-enables, set `error.stage = "think-mode-forced"`.
- Rate limit shown: set `error.stage = "rate-limited"`.
- Same set as `ask-gpt` otherwise.

Report `wrote runs/<slug>/raw/grok.json` when done.
