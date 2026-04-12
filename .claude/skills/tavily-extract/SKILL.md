---
name: tavily-extract
description: Extract full content from one or more URLs via Tavily. Use after tavily-search picks out authoritative sources (arxiv, nature, official docs) that warrant full-text retrieval.
---

You are invoking the `tavily` MCP server's extract tool.

## Inputs
- `slug`
- `urls` — array of URLs to extract (Tavily accepts up to ~20 at once)
- `extract_depth` — default `"advanced"`

## Call
```json
{
  "urls": ["https://...", "https://..."],
  "extract_depth": "advanced"
}
```

## Output
For each URL, write `runs/<slug>/raw/tavily/extract/<sanitized-domain-or-slug>.json`:
```json
{
  "source": "tavily-extract",
  "url": "<the URL>",
  "ts": "<UTC now>",
  "result": { /* verbatim Tavily extract item */ },
  "error": null
}
```

Filename slug: lowercase the domain + first path segment, strip non-alphanum to `-`. E.g. `arxiv.org/abs/2401.12345` → `arxiv-abs-2401-12345.json`.

## Failure
If Tavily returns no content for a URL, write the file with `result: null` and `error.stage = "no-content"`. Do not retry — downstream verifier handles it.
