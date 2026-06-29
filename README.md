# clean-search-mcp 🧹

A lightweight MCP (Model Context Protocol) service that provides **clean, spam-free search results** for AI agents. Filters out content farms, malware sites, SEO garbage, and low-quality content before they reach your LLM.

## Features

- **Three search engines** — Yandex + Bing + DuckDuckGo auto-fallback
- **176K+ domain blocklist** — auto-updated from 25+ community sources, covers malware/scam/ads/trackers/content farms
- **Three-layer filtering** — domain blacklist → content rules → quality scoring
- **Content extraction** — full page text via trafilatura + selectolax
- **Result scoring** — 0-1 quality score (official docs 0.8 > tutorials 0.6 > garbage 0)
- **LRU cache** — search cache 6h, fetch cache 24h, auto-cleanup
- **User blacklist** — add domains on the fly, report bad results
- **Deep mode** — optional Playwright fallback for JS-heavy pages
- **No heavy dependencies** — pure HTTP, no browser required

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## MCP Client Config

```json
{
  "mcpServers": {
    "clean-search": {
      "command": "python",
      "args": ["/path/to/clean_search_mcp/main.py"]
    }
  }
}
```

## Test Locally

```bash
python test_local.py "your search query" -n 5
python test_local.py "your query" -n 5 --no-content   # skip page content
python test_local.py "your query" --deep               # use Playwright fallback
```

## API

### `clean_search(query, max_results=5, with_content=True, deep_mode=False)`

| Param | Default | Description |
|-------|---------|-------------|
| `query` | required | Search query |
| `max_results` | 5 | Results to return (max 10) |
| `with_content` | True | Include extracted page text |
| `deep_mode` | False | Use Playwright fallback for JS pages |

Returns `[{title, url, snippet, content, score}]` sorted by quality.

### `add_user_blacklist(domain)`

Add a domain to personal blocklist.

### `report_bad_result(url)`

Report a low-quality URL (domain auto-blocked).

## Configuration

Edit `config.py` to tune:

- **Search providers**: enable/disable Yandex, Bing, DuckDuckGo
- **Blacklist sources**: add or remove community blocklist URLs
- **Scoring weights**: adjust domain authority, content quality bonuses
- **Caching**: TTL, max files, cleanup interval
- **Proxy**: set `PROXY` for HTTP/Playwright

## Dependencies

```
mcp, httpx, selectolax, trafilatura, duckduckgo-search
```

All lightweight pip packages. Playwright is optional (deep mode only).

## License

MIT
