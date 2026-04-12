---
name: tavily-search
description: Run a Tavily web search and save the raw results under runs/<slug>/raw/tavily/. Use inside research-scout when you need ranked web results for a query. Thin wrapper around the Tavily MCP search tool.
---

You are invoking the `tavily` MCP server's search tool.

## Inputs
- `slug`
- `query` — the exact search query
- `search_depth` — default `"advanced"` (matches `.mcp.json` DEFAULT_PARAMETERS)
- `max_results` — default 10
- `index` — integer for filename ordering when multiple searches in one run

## Call
Use `mcp__tavily__tavily-search` with:
```json
{
  "query": "<query>",
  "search_depth": "advanced",
  "max_results": 10,
  "include_raw_content": false,
  "include_images": false
}
```

## Output
Write `runs/<slug>/raw/tavily/search-<index>.json`:
```json
{
  "source": "tavily-search",
  "query": "<query>",
  "ts": "<UTC now>",
  "params": { "search_depth": "advanced", "max_results": 10 },
  "result": { /* verbatim Tavily response */ },
  "error": null
}
```

On any failure, still write the file with `result: null` and `error: {stage, message}`.

## Tip
When invoked from research-scout, prefer firing multiple `tavily-search` calls as one parallel batch — do not sequentially await each. See `research-scout.md`.
