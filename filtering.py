"""内容规则过滤 + URL 规范化 + 去重。"""
from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import config
from models import RawResult

_TRACKING_PARAMS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from","fr","fbclid","gclid","yclid","mc_cid","mc_eid","igshid","ref","ref_src"}


def canonical_url(url: str) -> str:
    try:
        p = urlsplit(url)
    except ValueError:
        return url
    query_items = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in _TRACKING_PARAMS]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", urlencode(query_items, doseq=True), ""))


def _dedup_key(title: str, content: str) -> str:
    return hashlib.md5((title + "\n" + content[:800]).strip().encode("utf-8", "ignore")).hexdigest()


def _spam_hits(text: str) -> int:
    low = text.lower()
    return sum(1 for kw in config.SPAM_KEYWORDS if kw.lower() in low)


def passes_prefetch_rules(raw: RawResult) -> bool:
    if not raw.url.startswith(("http://", "https://")):
        return False
    return _spam_hits(f"{raw.title}\n{raw.snippet}") < config.MAX_SPAM_HITS


def passes_post_rules(raw: RawResult, content: str) -> bool:
    if len(content) < config.MIN_CONTENT_LEN and len(raw.snippet or "") < config.MIN_SNIPPET_LEN:
        return False
    return _spam_hits(f"{raw.title}\n{raw.snippet}\n{content[:1500]}") < config.MAX_SPAM_HITS


def filter_pipeline(items: list[tuple[RawResult, str]]) -> list[tuple[RawResult, str]]:
    seen: set[str] = set()
    kept: list[tuple[RawResult, str]] = []
    for raw, content in items:
        if not passes_post_rules(raw, content):
            continue
        key = _dedup_key(raw.title, content or raw.snippet)
        if key in seen:
            continue
        seen.add(key)
        kept.append((raw, content))
    return kept
