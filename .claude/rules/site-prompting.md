# Site Prompting Conventions

Shared rules for every `ask-*` skill. When you drive an AI site through chrome-devtools MCP, shape the prompt you type into the site's composer using these rules. This is what makes answers from GPT, Gemini, NotebookLM, and Grok comparable downstream.

## The prompt envelope

Wrap the user's question in a stable envelope before sending it into the site's chat box:

```
[TeamX run <slug>] Answer the following question.

Rules:
- Respond in GitHub-flavored Markdown.
- Keep the answer under 600 words.
- At the end, include a "Sources" list with URLs (or say "no sources cited").
- If you are unsure, say so explicitly instead of guessing.

Question: <user's original question>
```

The `[TeamX run <slug>]` header is the cross-reference key. It is how you later match a transcript in the browser back to `runs/<slug>/raw/<source>.json`.

## Tab reuse protocol

Before touching any site:

Treat product-specific surfaces under a shared parent domain as different targets when they may run in parallel. Example: reserve `x.com/i/grok` for Grok and `x.com/search` for `scan-x`.

1. Call `list_pages`.
2. If any page is already open on the target domain, `select_page` one of those pages. Do this even if the page is on the wrong subpath.
3. Only call `new_page` when there is no open page on the target domain.
4. If the selected page needs to be reset, do it inside that same tab with `navigate_page` or the product's own "New chat" UI.
5. Never open a second tab for the same site just because the first attempt was on the wrong screen or conversation.

## Per-site deviations

- **ask-gpt**: no deviation. Plain envelope.
- **ask-gemini**: if the "Deep Research" toggle is visible, leave it OFF for MVP so latency stays bounded.
- **ask-notebooklm**: always select the active notebook first via the sidebar; if none is selected, fail fast with `error.stage = "no-notebook-selected"`.
- **ask-grok**: if a "Think" mode toggle exists, leave it OFF for MVP. Add a trailing line `Avoid speculation beyond what X posts support.`
- **scan-x**: this is a harvesting skill, not a prompt skill. It does not use the envelope. It uses advanced search URLs like `https://x.com/search?q=<query>&f=live`.

## Extraction rules

After the site finishes responding:

1. Wait for a stable response marker (no "Stop generating" button, no typing indicator).
2. Use `evaluate_script` to grab the raw markdown of only the last assistant message, not the entire thread.
3. Strip UI chrome (copy buttons, reaction counts) before saving to `answer_md`.
4. If the site shows inline citations or source chips, collect them into `citations[]` with `{title, url, snippet}`.
5. Capture the final `window.location.href` as `url` so you can link back to the conversation.

## When it goes wrong

If any of these happen, write the error stub and stop. Do not retry silently:

- The composer is not found after two snapshots: `error.stage = "composer-missing"`.
- The response never completes within 120s: `error.stage = "timeout"` and `take_screenshot` into `runs/<slug>/raw/<source>.png`.
- The page redirected to a login URL: `error.stage = "logged-out"`. The user must re-login in the attached Chrome.
- The site returned a refusal ("I can't help with that"): write it verbatim to `answer_md` and set `error.stage = "site-refused"`. Downstream verification decides how to treat it.
