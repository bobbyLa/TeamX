---
name: ask-notebooklm
description: Ask a question to Google NotebookLM with a pre-selected source notebook. Use when orchestrate-multi-ai's lineup includes NotebookLM. Requires an already-open notebook in the attached Chrome — NotebookLM only answers against the sources loaded into a specific notebook.
---

You are driving the browser-operator subagent to get a NotebookLM answer.

## Inputs
- `slug`, `question`
- `notebook_name` (optional) — if provided, the skill will select that notebook; otherwise it uses whichever notebook is currently open.

## Preconditions
- `notebooklm.google.com` logged in.
- A notebook is open or `notebook_name` is provided.
- **NotebookLM answers only against the notebook's sources** — if the notebook is empty or mismatched to the question, results will be poor. This is a known constraint.

## Playbook

1. `navigate_page` to `https://notebooklm.google.com/`.
2. If `notebook_name` provided: `take_snapshot`, find the notebook tile in the grid by accessible name, `click` it.
3. If no notebook is selected → **fail fast** with `error.stage = "no-notebook-selected"`. Do not guess.
4. Wait for the chat panel to load. `take_snapshot` again.
5. Find the composer `textbox` (usually labeled "Start typing..." or the question placeholder). `fill` with the envelope from `site-prompting.md`.
6. `click` the send button (arrow icon, accessible name "Submit" or "Send").
7. `wait_for` the response to complete — NotebookLM shows numbered citations inline; wait until the generating indicator stops. Timeout 180s (NotebookLM is slower).
8. `evaluate_script` to extract the answer text AND the numbered citation list:
   ```js
   (() => {
     const last = document.querySelectorAll('chat-message, [data-testid="chat-response"]');
     const el = last[last.length - 1];
     return el ? { text: el.innerText, html: el.innerHTML } : null;
   })()
   ```
9. Parse citations out of the HTML (they appear as clickable chips linking back into the notebook's sources). Populate `citations[]` with `{title, url: "notebook://<source-id>", snippet}`.
10. Write `runs/<slug>/raw/notebooklm.json`.

## Failure modes
- `no-notebook-selected` — stop, don't retry.
- Citation parsing failed → save the answer anyway with `citations: []` and a warning in `error.stage = "citations-unparsed"`.
- Otherwise same set as `ask-gpt`.

Report `wrote runs/<slug>/raw/notebooklm.json` when done.
