"""clean-search-mcp 入口。"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import config
from blacklist import add_user_domain, is_blocked, load_blacklist, report_bad_url
from extract import extract_main_text
from fetch import fetch_many
from filtering import canonical_url, filter_pipeline, passes_prefetch_rules
from scoring import score
from search import search

mcp = FastMCP("clean-search-mcp")


def _safe_result_limit(max_results: int) -> int:
    if not max_results:
        return config.RETURN_TOP_N
    return max(1, min(max_results, config.RETURN_MAX_N))


async def _run(query: str, max_results: int, with_content: bool, deep_mode: bool) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    limit = _safe_result_limit(max_results)
    fetch_n = min(max(config.SEARCH_FETCH_N, limit * 3), config.SEARCH_FETCH_MAX)
    raws = await search(query, fetch_n)
    if not raws:
        return []
    blacklist = await load_blacklist()
    survivors = []
    seen_urls: set[str] = set()
    for raw in raws:
        raw.url = canonical_url(raw.url)
        if raw.url in seen_urls:
            continue
        seen_urls.add(raw.url)
        if is_blocked(raw.url, blacklist):
            continue
        if not passes_prefetch_rules(raw):
            continue
        survivors.append(raw)
    if not survivors:
        return []
    htmls = await fetch_many([r.url for r in survivors], deep_mode=deep_mode)
    pairs = [(r, extract_main_text(htmls.get(r.url, ""))) for r in survivors]
    kept = filter_pipeline(pairs)
    scored = [score(r, c, query=query) for r, c in kept]
    scored.sort(key=lambda x: x.score, reverse=True)
    top = scored[:limit]
    out = []
    for item in top:
        d = item.to_public()
        if not with_content:
            d.pop("content", None)
        out.append(d)
    return out


@mcp.tool()
async def clean_search(query: str, max_results: int = config.RETURN_TOP_N, with_content: bool = True, deep_mode: bool = config.ENABLE_DEEP_MODE) -> list[dict]:
    """对 query 执行净化搜索，返回去广告/去内容农场后的高质量结果。

    Args:
        query: 搜索词
        max_results: 返回条数，默认 5，最大受 config.RETURN_MAX_N 限制
        with_content: 是否返回正文，默认 True
        deep_mode: httpx 失败后是否用 Playwright 兜底，慢但能处理部分 JS 页面
    """
    return await _run(query, max_results, with_content, deep_mode)


@mcp.tool()
async def add_user_blacklist(domain: str) -> dict:
    """添加用户级黑名单域名。"""
    ok = add_user_domain(domain)
    return {"ok": ok, "msg": "added" if ok else "invalid_domain_or_write_failed", "domain": domain}


@mcp.tool()
async def report_bad_result(url: str) -> dict:
    """上报低质结果（域名自动加入黑名单）。"""
    ok = report_bad_url(url)
    return {"ok": ok, "msg": "reported_and_domain_blocked" if ok else "invalid_url_or_write_failed", "url": url}


if __name__ == "__main__":
    mcp.run()
