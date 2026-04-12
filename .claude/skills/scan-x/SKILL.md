---
name: scan-x
description: Harvest a batch of X (Twitter) posts matching a query or from a user. Use when orchestrate-multi-ai wants raw public discourse signal on a topic, not an AI summary. Uses advanced search URLs, not the chat composer.
---

You are driving the browser-operator to collect public X posts. This is a harvesting skill — no prompt envelope, no AI interaction.

## Inputs
- `slug`
- `query` — either a free-text search string (e.g. `"MoE routing" -is:reply lang:en`) or a user handle (`from:<user>`)
- `max_posts` — default 30

## Preconditions
- Logged in to `x.com`.

## Playbook

1. Build the search URL: `https://x.com/search?q=<encoded query>&f=live`.
2. `navigate_page` to it.
3. `take_snapshot`. Verify at least one tweet `article` element is in the tree.
4. Loop up to `max_posts` collected or 10 scrolls (whichever first):
   - `evaluate_script` to scrape visible `<article>` elements into objects:
     ```js
     (() => Array.from(document.querySelectorAll('article'))
       .map(a => {
         const link = a.querySelector('a[href*="/status/"]');
         return {
           text: a.innerText,
           url: link ? new URL(link.href, location.origin).href : null,
           scraped_ts: new Date().toISOString()
         };
       })
       .filter(p => p.url)
     )()
     ```
   - Dedup by URL against what you already collected.
   - Scroll down via `evaluate_script`: `window.scrollBy(0, window.innerHeight * 2)`.
   - `wait_for` 1–2 seconds for new tweets to load (use a short explicit wait or re-snapshot).
5. Parse each collected `text` into `{author, posted_at, body}` best-effort (X's layout puts the author line first, body after).
6. Write `runs/<slug>/raw/x-scan.json`:
   ```json
   {
     "source": "x-scan",
     "query": "<the input query>",
     "ts": "<UTC now>",
     "posts": [{"author": "...", "ts": "...", "body": "...", "url": "..."}],
     "error": null
   }
   ```

## Failure modes
- Login wall → `stage: "logged-out"`.
- No results → write the file with `posts: []` and `error.stage = "no-results"`. Not a hard failure.
- Scroll stops producing new URLs before `max_posts` → stop early, write what you have.

Report `wrote runs/<slug>/raw/x-scan.json (<N> posts)` when done.
