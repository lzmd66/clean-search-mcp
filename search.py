"""搜索层：Bing HTML + duckduckgo_search，多 provider 兜底。"""
from __future__ import annotations

import asyncio
import importlib
from urllib.parse import urlparse, parse_qs, unquote

import httpx
from selectolax.parser import HTMLParser

import config
from cache import cache_get, cache_set, make_cache_key
from models import RawResult


def _dedup_results(items: list[RawResult]) -> list[RawResult]:
    seen: set[str] = set()
    out: list[RawResult] = []
    for item in items:
        url = item.url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out


def _headers() -> dict[str, str]:
    return {
        "User-Agent": config.USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def _unwrap_bing_url(url: str) -> str:
    try:
        p = urlparse(url)
    except ValueError:
        return url
    if "bing.com" not in p.netloc:
        return url
    qs = parse_qs(p.query)
    for key in ("u", "url"):
        if key in qs and qs[key]:
            return unquote(qs[key][0])
    return url


def _bing_search(query: str, n: int) -> list[RawResult]:
    timeout = httpx.Timeout(config.SEARCH_TIMEOUT)
    params = {"q": query, "count": str(n), "setlang": "zh-CN", "mkt": "zh-CN"}

    headers = {
        "User-Agent": config.USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(config.BING_SEARCH_URL, params=params)
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return []

    tree = HTMLParser(html)
    out: list[RawResult] = []
    for node in tree.css("li.b_algo"):
        a = node.css_first("h2 a")
        if not a:
            continue
        title = (a.text() or "").strip()
        url = _unwrap_bing_url(a.attributes.get("href", "").strip())
        snippet_node = node.css_first(".b_caption p") or node.css_first("p") or node.css_first(".b_dList")
        snippet = (snippet_node.text(separator=" ") if snippet_node else "").strip()
        if title and url.startswith(("http://", "https://")):
            out.append(RawResult(title=title, url=url, snippet=snippet))
        if len(out) >= n:
            break
    return _dedup_results(out)


def _yandex_search(query: str, n: int) -> list[RawResult]:
    """Yandex HTML 搜索结果抓取。俄中线路好，国内可用。"""
    timeout = httpx.Timeout(config.SEARCH_TIMEOUT)
    params = {"text": query, "numdoc": str(n), "lr": "115"}

    headers = {
        "User-Agent": config.USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ru;q=0.7",
    }

    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(config.YANDEX_SEARCH_URL, params=params)
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return []

    tree = HTMLParser(html)
    out: list[RawResult] = []

    # Yandex 结果格式: <li class="serp-item">...<h2><a href="url">title</a></h2>...
    for node in tree.css("li.serp-item"):
        a = node.css_first("h2 a")
        if not a:
            a = node.css_first("a.link")
        if not a:
            continue
        title = (a.text() or "").strip()
        href = a.attributes.get("href", "").strip()
        if not title or not href:
            continue

        snippet_node = node.css_first(".text-container") or node.css_first(". Passage") or node.css_first("div.text")
        snippet = (snippet_node.text(separator=" ") if snippet_node else "").strip()
        out.append(RawResult(title=title, url=href, snippet=snippet))
        if len(out) >= n:
            break

    return _dedup_results(out)


def _new_ddgs_client(ddgs_cls):
    kwargs = {}
    if config.PROXY:
        kwargs["proxy"] = config.PROXY
    try:
        return ddgs_cls(timeout=config.SEARCH_TIMEOUT, **kwargs)
    except TypeError:
        try:
            return ddgs_cls(**kwargs)
        except TypeError:
            return ddgs_cls()


def _duckduckgo_search(query: str, n: int) -> list[RawResult]:
    mod = importlib.import_module("duckduckgo_search")
    ddgs_cls = getattr(mod, "DDGS")
    client = _new_ddgs_client(ddgs_cls)
    out: list[RawResult] = []
    if hasattr(client, "__enter__"):
        with client as ddgs:
            rows = ddgs.text(query, max_results=n)
            for r in rows:
                url = r.get("href") or r.get("url") or ""
                title = r.get("title") or ""
                snippet = r.get("body") or r.get("snippet") or ""
                if url:
                    out.append(RawResult(title=title, url=url, snippet=snippet))
    else:
        try:
            rows = client.text(query, max_results=n)
            for r in rows:
                url = r.get("href") or r.get("url") or ""
                title = r.get("title") or ""
                snippet = r.get("body") or r.get("snippet") or ""
                if url:
                    out.append(RawResult(title=title, url=url, snippet=snippet))
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
    return _dedup_results(out)


_PROVIDER_MAP = {"yandex": _yandex_search, "bing": _bing_search, "duckduckgo": _duckduckgo_search}


def _sync_search(query: str, n: int) -> list[RawResult]:
    merged: list[RawResult] = []
    for name in config.SEARCH_PROVIDERS:
        fn = _PROVIDER_MAP.get(name)
        if not fn:
            continue
        try:
            results = fn(query, n)
        except Exception:
            continue
        if results:
            merged.extend(results)
        if len(_dedup_results(merged)) >= n:
            break
    return _dedup_results(merged)[:n]


async def search(query: str, n: int = config.SEARCH_FETCH_N) -> list[RawResult]:
    n = max(1, min(n, config.SEARCH_FETCH_MAX))
    cache_key = make_cache_key("search", query, str(n), ",".join(config.SEARCH_PROVIDERS))
    if config.ENABLE_SEARCH_CACHE:
        cached = cache_get(cache_key, config.SEARCH_CACHE_TTL)
        if isinstance(cached, list):
            return [RawResult(title=str(x.get("title","")), url=str(x.get("url","")), snippet=str(x.get("snippet",""))) for x in cached if isinstance(x, dict) and x.get("url")]
    results = await asyncio.to_thread(_sync_search, query, n)
    if config.ENABLE_SEARCH_CACHE and results:
        cache_set(cache_key, [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results])
    return results
