"""静态黑名单 + 用户黑名单 + 远程订阅，断网时用过期缓存兜底。"""
from __future__ import annotations

import os
import re
import time
from urllib.parse import urlparse

import httpx

import config

_RULE_RE = re.compile(r"^\*://(?:\*\.)?([a-z0-9.-]+)/", re.I)
_UBLOCK_DOMAIN_RE = re.compile(r"^\|\|([a-z0-9.-]+)\^", re.I)
_HOSTS_RE = re.compile(r"^(?:0\.0\.0\.0|127\.0\.0\.1)\s+([a-z0-9.-]+)", re.I)
_DOMAIN_RE = re.compile(r"^(?:[a-z0-9-]+\.)+[a-z]{2,}$", re.I)


def _clean_domain(domain: str) -> str:
    domain = domain.strip().lower()
    domain = domain.removeprefix("http://").removeprefix("https://")
    domain = domain.removeprefix("www.")
    domain = domain.split("/", 1)[0]
    domain = domain.split(":", 1)[0]
    return domain.strip(".")


def _parse_subscription(text: str) -> set[str]:
    domains: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "!", "@")):
            continue
        for rx in (_RULE_RE, _UBLOCK_DOMAIN_RE, _HOSTS_RE):
            m = rx.match(line)
            if m:
                domain = _clean_domain(m.group(1))
                if _DOMAIN_RE.match(domain):
                    domains.add(domain)
                break
        else:
            candidate = _clean_domain(line)
            if _DOMAIN_RE.match(candidate):
                domains.add(candidate)
    return domains


def _load_cache(max_age: float | None) -> set[str] | None:
    path = config.BLACKLIST_CACHE_FILE
    if not os.path.exists(path):
        return None
    if max_age is not None:
        try:
            if time.time() - os.path.getmtime(path) > max_age:
                return None
        except OSError:
            return None
    try:
        with open(path, encoding="utf-8") as f:
            return {_clean_domain(ln) for ln in f if _clean_domain(ln)}
    except OSError:
        return None


def _load_fresh_cache() -> set[str] | None:
    return _load_cache(config.BLACKLIST_TTL)


def _load_stale_cache() -> set[str] | None:
    return _load_cache(config.BLACKLIST_CACHE_GRACE)


def _save_cache(domains: set[str]) -> None:
    try:
        with open(config.BLACKLIST_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(domains)))
    except OSError:
        pass


def _load_user_blacklist() -> set[str]:
    path = config.USER_BLACKLIST_FILE
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            return {_clean_domain(ln) for ln in f if _clean_domain(ln)}
    except OSError:
        return set()


def add_user_domain(domain: str) -> bool:
    domain = _clean_domain(domain)
    if not _DOMAIN_RE.match(domain):
        return False
    current = _load_user_blacklist()
    current.add(domain)
    try:
        with open(config.USER_BLACKLIST_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(current)))
        return True
    except OSError:
        return False


def report_bad_url(url: str) -> bool:
    domain = _domain_of(url)
    if not domain:
        return False
    try:
        with open(config.BAD_RESULT_FILE, "a", encoding="utf-8") as f:
            f.write(url.strip() + "\n")
    except OSError:
        return False
    return add_user_domain(domain)


async def load_blacklist() -> set[str]:
    static = set(config.STATIC_BLACKLIST)
    user = _load_user_blacklist()
    fresh = _load_fresh_cache()
    if fresh is not None:
        return static | user | fresh

    remote: set[str] = set()
    timeout = httpx.Timeout(config.SEARCH_TIMEOUT)
    client_kwargs = {"timeout": timeout, "follow_redirects": True}
    if config.PROXY:
        client_kwargs["proxy"] = config.PROXY
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            for url in config.BLACKLIST_SUBSCRIPTIONS:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    remote |= _parse_subscription(resp.text)
                except (httpx.HTTPError, UnicodeError):
                    continue
    except TypeError:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for url in config.BLACKLIST_SUBSCRIPTIONS:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    remote |= _parse_subscription(resp.text)
                except (httpx.HTTPError, UnicodeError):
                    continue

    if remote:
        _save_cache(remote)
        return static | user | remote

    stale = _load_stale_cache()
    if stale is not None:
        return static | user | stale
    return static | user


def _domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def is_blocked(url: str, blacklist: set[str]) -> bool:
    host = _domain_of(url)
    if not host:
        return True
    parts = host.split(".")
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in blacklist:
            return True
    return False


domain_of = _domain_of
