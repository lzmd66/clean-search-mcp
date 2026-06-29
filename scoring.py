"""rule-based 0~1 评分：源站权威度 + 内容质量 + 反 SEO 噪声。"""
from __future__ import annotations

import re

import config
from blacklist import domain_of
from models import CleanResult, RawResult

_WORD_RE = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]+")


def _domain_weight(host: str) -> tuple[float, str]:
    for domain, weight in config.TRUSTED_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return weight, f"trusted_domain:{domain}+{weight}"
    for domain, weight in config.LOW_QUALITY_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return weight, f"low_quality_domain:{domain}{weight}"
    return (0.14, "base_domain+0.14") if host else (0.0, "no_domain+0")


def _content_quality(content: str) -> tuple[float, str]:
    length = len(content or "")
    if length >= 5000:
        return 0.24, "long_content+0.24"
    if length >= 2000:
        return 0.20, "good_content+0.20"
    if length >= config.MIN_CONTENT_LEN:
        return 0.14, "has_content+0.14"
    if length > 0:
        return 0.04, "thin_content+0.04"
    return 0.0, "no_content+0"


def _snippet_quality(snippet: str) -> tuple[float, str]:
    length = len(snippet or "")
    if length >= 160:
        return 0.12, "rich_snippet+0.12"
    if length >= config.MIN_SNIPPET_LEN * 2:
        return 0.08, "ok_snippet+0.08"
    if length >= config.MIN_SNIPPET_LEN:
        return 0.04, "short_snippet+0.04"
    return 0.0, "no_snippet+0"


def _query_relevance(query: str, raw: RawResult, content: str) -> tuple[float, str]:
    q_terms = set(t.lower() for t in _WORD_RE.findall(query) if len(t.strip()) >= 2)
    if not q_terms:
        return 0.0, "no_query_terms+0"
    title, snippet, body = raw.title.lower(), raw.snippet.lower(), content[:3000].lower()
    hits = sum(1.5 if t in title else 1.0 if t in snippet else 0.5 if t in body else 0.0 for t in q_terms)
    val = round(0.18 * min(1.0, hits / max(1.0, len(q_terms))), 3)
    return val, f"query_relevance+{val}"


def _spam_penalty(raw: RawResult, content: str) -> tuple[float, str]:
    text = f"{raw.title}\n{raw.snippet}\n{content[:2000]}".lower()
    hits = sum(1 for kw in config.SPAM_KEYWORDS if kw.lower() in text)
    if hits <= 0:
        return 0.10, "no_spam+0.10"
    return -min(0.25, hits * 0.08), f"spam_hits:{hits}{-min(0.25, hits * 0.08)}"


def _seo_penalty(title: str) -> tuple[float, str]:
    sep_count = sum(title.count(c) for c in "|-_—»·")
    if sep_count >= 5:
        return -0.08, "seo_title-0.08"
    if sep_count >= 3:
        return -0.04, "mild_seo_title-0.04"
    return 0.0, "clean_title+0"


def _content_shape_bonus(content: str) -> tuple[float, str]:
    if not content:
        return 0.0, "no_shape_bonus+0"
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return 0.0, "no_shape_bonus+0"
    avg = sum(len(ln) for ln in lines) / max(1, len(lines))
    if len(lines) >= 20 and avg < 18:
        return -0.06, "fragmented_content-0.06"
    if len(lines) >= 5 and avg >= 40:
        return 0.06, "paragraph_content+0.06"
    return 0.0, "neutral_shape+0"


def score(raw: RawResult, content: str, query: str = "") -> CleanResult:
    host = domain_of(raw.url)
    parts = [_domain_weight(host), _content_quality(content), _snippet_quality(raw.snippet),
             _query_relevance(query, raw, content), _spam_penalty(raw, content),
             _seo_penalty(raw.title), _content_shape_bonus(content)]
    total = max(0.0, min(1.0, sum(v for v, _ in parts)))
    return CleanResult(title=raw.title, url=raw.url, snippet=raw.snippet, content=content, score=round(total, 3), reasons=[r for _, r in parts])
