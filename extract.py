"""正文抽取：trafilatura 优先，selectolax 兜底。"""
from __future__ import annotations

import re

_WS_RE = re.compile(r"[ \t\r\f\v]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def _normalize(text: str) -> str:
    text = _WS_RE.sub(" ", text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return _MULTI_NL_RE.sub("\n\n", "\n".join(lines)).strip()


def _extract_by_trafilatura(html: str) -> str:
    import trafilatura
    text = trafilatura.extract(html, include_comments=False, include_tables=False, favor_precision=True, no_fallback=False)
    return _normalize(text or "")


def _node_text(node) -> str:
    try:
        return node.text(separator="\n")
    except TypeError:
        return node.text()


def _score_text_block(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    punctuation = sum(text.count(c) for c in "，。！？；：,.!?;:")
    return len(text) + chinese_chars * 2 + punctuation * 8


def _extract_by_selectolax(html: str) -> str:
    from selectolax.parser import HTMLParser
    tree = HTMLParser(html)
    for css in ("script", "style", "noscript", "svg", "canvas", "iframe", "nav", "footer", "header", "aside", "form",
                ".comment", ".comments", ".sidebar", ".advertisement", ".ads",
                "#comment", "#comments", "#sidebar"):
        for node in tree.css(css):
            node.decompose()
    candidates = []
    for css in ("article", "main", '[role="main"]', ".article", ".post", ".content",
                ".post-content", ".entry-content", ".article-content", "#content", "body"):
        for node in tree.css(css):
            text = _normalize(_node_text(node))
            if text:
                candidates.append((_score_text_block(text), text))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def extract_main_text(html: str) -> str:
    if not html:
        return ""
    try:
        text = _extract_by_trafilatura(html)
    except Exception:
        text = ""
    if text:
        return text
    try:
        return _extract_by_selectolax(html)
    except Exception:
        return ""
