"""Single HTTP seam for TokenMiner.

All network access (collectors, validators) goes through :class:`HttpClient`
so tests can mock one seam and politeness/retry/caching is enforced once.

Policy (SPEC §32): one UA, timeout, retries with exponential backoff,
>=1s politeness delay per host, in-run cache keyed by URL.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

USER_AGENT = "TokenMiner/0.1 (+https://github.com/tokenminer/TokenMiner)"
DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 3
POLITENESS_DELAY = 1.0  # seconds between requests to the same host


@dataclass
class FetchResult:
    """Minimal response record (cacheable, re-readable)."""

    url: str
    final_url: str
    status: int
    text: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class HttpClient:
    """httpx.Client wrapper with retry/backoff, politeness and caching."""

    def __init__(
        self,
        user_agent: str = USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        politeness: float = POLITENESS_DELAY,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries
        self.politeness = politeness
        self._cache: dict[str, FetchResult] = {}
        self._last_request_at: dict[str, float] = {}
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    def _be_polite(self, url: str) -> None:
        host = urlsplit(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            wait = self.politeness - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_request_at[host] = time.monotonic()

    def fetch(self, url: str) -> FetchResult | None:
        """GET ``url``; follow redirects; return FetchResult or None on failure."""
        if url in self._cache:
            return self._cache[url]
        result: FetchResult | None = None
        backoff = 1.0
        for attempt in range(1, self.retries + 1):
            self._be_polite(url)
            try:
                resp = self._client.get(url)
                result = FetchResult(url, str(resp.url), resp.status_code, resp.text)
                break
            except httpx.HTTPError:
                if attempt == self.retries:
                    result = None
                    break
                time.sleep(backoff)
                backoff *= 2
        if result is not None:
            self._cache[url] = result
        return result

    def get_text(self, url: str) -> str | None:
        """Response body text (2xx only) or None."""
        result = self.fetch(url)
        if result is not None and result.ok:
            return result.text
        return None

    def get_json(self, url: str) -> Any | None:
        """Parsed JSON body (2xx only) or None."""
        text = self.get_text(url)
        if text is None:
            return None
        try:
            import json

            return json.loads(text)
        except ValueError:
            return None
