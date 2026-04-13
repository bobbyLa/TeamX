---
name: ask-gemini
description: Ask a question to Google Gemini via the already-logged-in gemini.google.com session in the attached Chrome. Use when orchestrate-multi-ai's lineup includes Gemini. Requires chrome-devtools MCP attached to a Chrome with an active Google login.
---

You are driving the browser-operator subagent to get a Gemini answer. Same shape as `ask-gpt`; only the site-specific bits differ.

## Inputs
- `slug`, `question`

## Preconditions
- `gemini.google.com` logged in.
- Deep Research toggle is OFF (see `.claude/rules/site-prompting.md` under "Per-site deviations").

## Playbook

1. Apply `.claude/rules/site-prompting.md` under "Tab reuse protocol" for `gemini.google.com`.
2. If the selected tab is in an old conversation, reset inside that same tab: prefer Gemini's "New chat" UI, and only fall back to `navigate_page` to `https://gemini.google.com/app`.
3. `take_snapshot`. Find the composer `textbox` named "Enter a prompt here" (or equivalent). Capture its UID.
4. Build the prompt envelope from `site-prompting.md` and `fill` the composer.
5. Find the send button (role `button` named "Send message"); `click` or press Enter.
6. `wait_for` the "Stop response" control to disappear and "Show drafts" or "Copy" controls to appear. Timeout 120s.
7. `evaluate_script` to extract the last assistant turn:
   ```js
   (() => {
     const turns = document.querySelectorAll('message-content, [data-response-index]');
     const last = turns[turns.length - 1];
     return last ? last.innerText : null;
   })()
   ```
   Fallback: take the last `<model-response>` element if present.
8. Capture any inline citation chips into `citations[]` when visible. Gemini often surfaces them.
9. Write `runs/<slug>/raw/gemini.json` per the output contract.

## Failure modes
Same set as `ask-gpt`. Additionally:
- Deep Research got auto-enabled: disable and retry once; if it stays on, set `error.stage = "deep-research-on"`.
- Country or age-gate overlay: set `error.stage = "gate-overlay"`.

Report `wrote runs/<slug>/raw/gemini.json` when done.
