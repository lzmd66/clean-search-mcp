"""异步抓取 + 流式限量读取 + 轻量反爬 + 可选 Playwright deep mode。"""
from __future__ import annotations

import asyncio
import random

import httpx

import config
from cache import cache_get, cache_set, make_cache_key


def _headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache", "Pragma": "no-cache", "Connection": "keep-alive",
    }


def _is_probably_text_response(content_type: str) -> bool:
    if not content_type:
        return True
    low = content_type.lower()
    return any(x in low for x in ("html", "text", "xml", "json"))


def _is_challenge(status: int, body: str) -> bool:
    if status in (403, 429, 503):
        return True
    low = body[:5000].lower()
    return any(m in low for m in config.CHALLENGE_MARKERS)


async def _read_limited_text(resp: httpx.Response) -> str:
    chunks: list[bytes] = []
    total = 0
    async for chunk in resp.aiter_bytes():
        if not chunk:
            continue
        next_total = total + len(chunk)
        if next_total > config.MAX_CONTENT_BYTES:
            remain = config.MAX_CONTENT_BYTES - total
            if remain > 0:
                chunks.append(chunk[:remain])
            break
        chunks.append(chunk)
        total = next_total
    data = b"".join(chunks)
    encoding = resp.encoding or "utf-8"
    try:
        return data.decode(encoding, errors="ignore")
    except LookupError:
        return data.decode("utf-8", errors="ignore")


async def _fetch_one_httpx(client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore) -> str:
    async with sem:
        try:
            async with client.stream("GET", url, headers=_headers(), follow_redirects=True) as resp:
                ctype = resp.headers.get("content-type", "")
                if not _is_probably_text_response(ctype):
                    return ""
                body = await _read_limited_text(resp)
                if _is_challenge(resp.status_code, body):
                    return ""
                return body
        except (httpx.HTTPError, UnicodeError):
            return ""


async def _fetch_many_httpx(urls: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    sem = asyncio.Semaphore(config.MAX_CONCURRENCY)
    timeout = httpx.Timeout(config.FETCH_TIMEOUT)
    limits = httpx.Limits(max_connections=config.MAX_CONCURRENCY, max_keepalive_connections=config.MAX_CONCURRENCY)
    client_kwargs = {"timeout": timeout, "limits": limits}
    if config.PROXY:
        client_kwargs["proxy"] = config.PROXY
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            tasks = [_fetch_one_httpx(client, url, sem) for url in urls]
            htmls = await asyncio.gather(*tasks)
    except TypeError:
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            tasks = [_fetch_one_httpx(client, url, sem) for url in urls]
            htmls = await asyncio.gather(*tasks)
    for url, html in zip(urls, htmls):
        result[url] = html
    return result


async def _fetch_one_playwright(page, url: str) -> str:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=int(config.DEEP_FETCH_TIMEOUT * 1000))
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
        html = await page.content()
        if _is_challenge(200, html):
            return ""
        return html[: config.MAX_CONTENT_BYTES]
    except Exception:
        return ""


async def _fetch_many_playwright(urls: list[str]) -> dict[str, str]:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return {url: "" for url in urls}
    result: dict[str, str] = {}
    try:
        async with async_playwright() as p:
            browser_kwargs = {"headless": True}
            if config.PROXY:
                browser_kwargs["proxy"] = {"server": config.PROXY}
            browser = await p.chromium.launch(**browser_kwargs)
            context = await browser.new_context(user_agent=random.choice(config.USER_AGENTS), locale="zh-CN", viewport={"width": 1365, "height": 768})
            sem = asyncio.Semaphore(max(1, min(config.MAX_CONCURRENCY, 3)))
            async def run(url: str) -> tuple[str, str]:
                async with sem:
                    page = await context.new_page()
                    try:
                        html = await _fetch_one_playwright(page, url)
                        return url, html
                    finally:
                        await page.close()
            pairs = await asyncio.gather(*(run(url) for url in urls))
            for url, html in pairs:
                result[url] = html
            await context.close()
            await browser.close()
    except Exception:
        return {url: "" for url in urls}
    return result


async def _fetch_one_scrapling(url: str) -> str:
    """用本地 Scrapling 服务抓取（能过 Cloudflare 和反爬）。"""
    try:
        import httpx as _h
        resp = await _h.AsyncClient(timeout=15).get(
            "http://127.0.0.1:18083/fetch-text",
            params={"url": url},
        )
        if resp.status_code == 200:
            data = resp.json()
            return (data.get("text") or data.get("result") or "")[: config.MAX_CONTENT_BYTES]
        return ""
    except Exception:
        return ""


async def fetch_many(urls: list[str], deep_mode: bool = False) -> dict[str, str]:
    if not urls:
        return {}
    unique_urls = list(dict.fromkeys(urls))
    result: dict[str, str] = {}
    misses: list[str] = []
    for url in unique_urls:
        cache_key = make_cache_key("fetch", url, "deep" if deep_mode else "normal")
        cached = cache_get(cache_key, config.FETCH_CACHE_TTL) if config.ENABLE_FETCH_CACHE else None
        if isinstance(cached, str):
            result[url] = cached
        else:
            misses.append(url)
    if not misses:
        return result
    httpx_result = await _fetch_many_httpx(misses)
    need_deep: list[str] = []
    for url in misses:
        html = httpx_result.get(url, "")
        result[url] = html
        if deep_mode and not html:
            need_deep.append(url)
    if deep_mode and need_deep:
        need_deep = need_deep[: max(0, int(config.DEEP_MAX_PAGES))]
        deep_result = await _fetch_many_playwright(need_deep)
        for url, html in deep_result.items():
            if html:
                result[url] = html

    # Scrapling 兜底：httpx 和 Playwright 都抓不到时，走本地爬虫
    scrapling_urls = [url for url in misses if not result.get(url)]
    if scrapling_urls:
        for url in scrapling_urls:
            html = await _fetch_one_scrapling(url)
            if html:
                result[url] = html
    for url in misses:
        html = result.get(url, "")
        if config.ENABLE_FETCH_CACHE and html:
            cache_set(make_cache_key("fetch", url, "deep" if deep_mode else "normal"), html)
    return result
