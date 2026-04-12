---
name: tavily-crawl
description: Systematically crawl a website starting from a root URL via Tavily. Use sparingly — only when the question requires broad coverage of a single site (e.g. a docs portal). For most research, tavily-search + tavily-extract is enough.
---

You are invoking the `tavily` MCP server's crawl tool.

## Inputs
- `slug`
- `root_url` — the starting URL
- `max_depth` — default 2
- `limit` — default 30 pages (keep tight; crawl is expensive)
- `instructions` — optional natural-language focus, e.g. "only pages about API authentication"

## Call
```json
{
  "url": "<root_url>",
  "max_depth": 2,
  "limit": 30,
  "instructions": "<optional focus>"
}
```

## Output
Write `runs/<slug>/raw/tavily/crawl/<domain>.json`:
```json
{
  "source": "tavily-crawl",
  "root_url": "<root_url>",
  "ts": "<UTC now>",
  "params": { "max_depth": 2, "limit": 30 },
  "result": { /* verbatim Tavily crawl response */ },
  "error": null
}
```

## Guardrails
- Never crawl without an explicit `root_url` input.
- Never crawl inside `orchestrate-multi-ai`'s default fan-out — crawl is opt-in per run.
- If the crawl would exceed `limit` pages, trust Tavily's cap; don't raise it.
