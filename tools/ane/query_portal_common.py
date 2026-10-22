"""Shared safeguards for bounded, case-by-case public database queries."""

from __future__ import annotations

import fcntl
import hashlib
import html as html_module
import json
import os
import re
import ssl
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

USER_AGENT = "kaphtor/1.0 (bounded scholarly consultation)"


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def clean(fragment: str, *, preserve_lines: bool = False) -> str:
    fragment = html_module.unescape(fragment)
    if preserve_lines:
        fragment = re.sub(r"<lb\b[^>]*/?>", "\n", fragment, flags=re.IGNORECASE)
        fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    else:
        fragment = re.sub(r"<(?:lb|br)\b[^>]*/?>", " ", fragment, flags=re.IGNORECASE)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html_module.unescape(fragment).replace("\xa0", " ")
    if not preserve_lines:
        return re.sub(r"\s+", " ", fragment).strip()
    lines = [re.sub(r"\s+", " ", line).strip() for line in fragment.splitlines()]
    return "\n".join(line for line in lines if line)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def cache_path(cache: Path, mode: str, parameters: dict[str, Any]) -> Path:
    fingerprint = hashlib.sha256(
        json.dumps([mode, parameters], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    return cache / f"{mode}-{fingerprint}.json"


def load_cache(path: Path, refresh: bool) -> dict[str, Any] | None:
    if refresh or not path.exists():
        return None
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    wrapper["source_request_count"] = wrapper.get("source_request_count", 1)
    wrapper["network_request_count"] = 0
    wrapper["cache_hit"] = True
    return wrapper


def save_cache(path: Path, wrapper: dict[str, Any]) -> None:
    stored = {**wrapper, "cache_hit": False}
    atomic_write(
        path,
        (json.dumps(stored, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def throttle(state_path: Path, delay: float) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("a+", encoding="utf-8") as state:
        fcntl.flock(state.fileno(), fcntl.LOCK_EX)
        state.seek(0)
        raw = state.read().strip()
        previous = float(raw) if raw else 0.0
        wait = max(0.0, delay - (time.time() - previous))
        if wait:
            time.sleep(wait)
        started = time.time()
        state.seek(0)
        state.truncate()
        state.write(f"{started:.6f}\n")
        state.flush()
        fcntl.flock(state.fileno(), fcntl.LOCK_UN)


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def request_bytes(
    source: str,
    url: str,
    *,
    rate_state: Path,
    delay: float,
    data: bytes | None = None,
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9",
) -> bytes:
    throttle(rate_state, delay)
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    try:
        with urllib.request.urlopen(request, timeout=60, context=ssl_context()) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"{source} returned HTTP {exc.code}: {detail[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"{source} request failed: {exc}") from exc
