---
name: ask-gemini
description: Ask a question to Google Gemini via the already-logged-in gemini.google.com session in the attached Chrome. Use when orchestrate-multi-ai's lineup includes Gemini. Requires chrome-devtools MCP attached to a Chrome with an active Google login.
---

You are driving the browser-operator subagent to get a Gemini answer. Same shape as `ask-gpt` — only the site-specific bits differ.

## Inputs
- `slug`, `question`

## Preconditions
- `gemini.google.com` logged in.
- Deep Research toggle is OFF (see `.claude/rules/site-prompting.md` § "Per-site deviations").

## Playbook

1. `list_pages` / `new_page` to `https://gemini.google.com/app`. Start a new chat if an old one is open (click "New chat" or visit `/app` directly).
2. `take_snapshot`. Find the composer `textbox` named "Enter a prompt here" (or equivalent). Capture its UID.
3. Build the prompt envelope from `site-prompting.md` and `fill` the composer.
4. Find the send button (role `button` named "Send message"); `click` or press Enter.
5. `wait_for` the "Stop response" control to disappear AND "Show drafts" / "Copy" controls to appear. Timeout 120s.
6. `evaluate_script` to extract the last assistant turn:
   ```js
   (() => {
     const turns = document.querySelectorAll('message-content, [data-response-index]');
     const last = turns[turns.length - 1];
     return last ? last.innerText : null;
   })()
   ```
   Fallback: take the last `<model-response>` element if present.
7. Capture any inline citation chips into `citations[]` when visible — Gemini often surfaces them.
8. Write `runs/<slug>/raw/gemini.json` per the output contract.

## Failure modes
Same set as `ask-gpt`. Additionally:
- Deep Research got auto-enabled → `stage: "deep-research-on"` (disable and retry once).
- Country/age-gate overlay → `stage: "gate-overlay"`.

Report `wrote runs/<slug>/raw/gemini.json` when done.
