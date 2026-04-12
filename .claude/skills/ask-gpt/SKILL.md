---
name: ask-gpt
description: Ask a question to ChatGPT via the already-logged-in chat.openai.com session in the attached Chrome. Use when orchestrate-multi-ai's lineup includes GPT. Requires chrome-devtools MCP attached to a Chrome with an active ChatGPT login.
---

You are driving the browser-operator subagent to get a ChatGPT answer.

## Inputs
- `slug` — the current run slug
- `question` — the user's original question

## Preconditions
- Chrome is attached via `--browserUrl` (see `.mcp.json`).
- `chatgpt.com` has an active logged-in session.

## Playbook

1. **Open the page**
   - `list_pages` → if a chatgpt.com tab is open, `select_page` it; otherwise `new_page` to `https://chatgpt.com/`.
   - `navigate_page` to `https://chatgpt.com/` if the current URL is a specific conversation (start fresh).

2. **Snapshot and find the composer**
   - `take_snapshot`.
   - In the a11y tree, find the element with role `textbox` whose accessible name contains "Message" or "Send a message". Capture its UID.

3. **Send the prompt**
   - Build the prompt envelope from `.claude/rules/site-prompting.md`, substituting `<slug>` and the question.
   - `fill` the composer UID with the envelope string.
   - Find the send button (role `button`, name "Send" or equivalent arrow icon). `click` it.
     - Fallback: `press_key` "Enter" on the composer UID.

4. **Wait for completion**
   - `wait_for` until the "Stop generating" button disappears AND a "Regenerate" / "Copy" action appears on the last turn. Timeout 120s.

5. **Extract the last assistant message**
   - `evaluate_script` something like:
     ```js
     (() => {
       const turns = document.querySelectorAll('[data-message-author-role="assistant"]');
       const last = turns[turns.length - 1];
       return last ? last.innerText : null;
     })()
     ```
   - Also capture `window.location.href` and any visible model name in the header.

6. **Write the artifact**
   - Write `runs/<slug>/raw/gpt.json` in the shape from `.claude/rules/output-contract.md`:
     ```json
     {
       "source": "gpt",
       "model": "<from header, e.g. 'gpt-4o'>",
       "question": "<the envelope you sent>",
       "answer_md": "<extracted text>",
       "url": "<window.location.href>",
       "ts": "<UTC now>",
       "citations": [],
       "error": null
     }
     ```

## Failure modes
- Composer UID not found → write error stub with `stage: "composer-missing"` and `take_screenshot` into `runs/<slug>/raw/gpt.png`.
- Timeout waiting for completion → `stage: "timeout"`.
- Redirected to login → `stage: "logged-out"`.
- See `.claude/rules/site-prompting.md` § "When it goes wrong".

Report only `wrote runs/<slug>/raw/gpt.json` when done.
