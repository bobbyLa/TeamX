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

1. `navigate_page` to `https://grok.com/` (or `https://x.com/i/grok` if grok.com is unavailable — try grok.com first).
2. `take_snapshot`. Find the composer `textbox`. On grok.com it's usually labeled "Ask anything" or similar.
3. Build the envelope from `site-prompting.md` and append the trailing line `Avoid speculation beyond what X posts support.` per the Grok deviation rule.
4. `fill` the composer, `click` send (or Enter).
5. `wait_for` the response to complete. Timeout 120s.
6. `evaluate_script` to extract the last assistant turn and any cited X posts. Grok often renders post cards inline — capture their URLs into `citations[]`.
7. Write `runs/<slug>/raw/grok.json`.

## Failure modes
- Think mode auto-enabled → disable and retry once; if it re-enables, `stage: "think-mode-forced"`.
- Rate limit shown → `stage: "rate-limited"`.
- Same set as `ask-gpt` otherwise.

Report `wrote runs/<slug>/raw/grok.json` when done.
