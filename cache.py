from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any

import config

_last_cleanup = 0.0


def _cache_dir() -> Path:
    path = Path(config.CACHE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_cache_key(prefix: str, *parts: str) -> str:
    h = hashlib.sha256()
    h.update(prefix.encode("utf-8"))
    for part in parts:
        h.update(b"\0")
        h.update(part.encode("utf-8", "ignore"))
    return f"{prefix}_{h.hexdigest()}.json"


def cleanup_cache(force: bool = False) -> None:
    global _last_cleanup
    now = time.time()
    if not force and now - _last_cleanup < config.CACHE_CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    try:
        files = [p for p in _cache_dir().glob("*.json") if p.is_file()]
    except OSError:
        return
    max_files = max(100, int(config.CACHE_MAX_FILES))
    if len(files) <= max_files:
        return
    try:
        files.sort(key=lambda p: p.stat().st_mtime)
    except OSError:
        return
    for path in files[: max(0, len(files) - max_files)]:
        try:
            path.unlink()
        except OSError:
            pass


def cache_get(key: str, ttl: int | float) -> Any | None:
    if random.random() < 0.02:
        cleanup_cache()
    path = _cache_dir() / key
    try:
        stat = path.stat()
    except OSError:
        return None
    if time.time() - stat.st_mtime > ttl:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("value")


def cache_set(key: str, value: Any) -> None:
    path = _cache_dir() / key
    try:
        path.write_text(json.dumps({"value": value}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
