"""Generic collector (SPEC §14).

For providers without a dedicated collector: fetch the provider's
``watch_urls``, extract visible text, keyword-scan for deal terms, store a
content-hash snapshot per provider (data/generic_state.json), and flag
changes versus the last run. Its job is change detection, not understanding
the page — JS-only shells produce tiny text and are hashed as-is (no crash).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from bs4 import BeautifulSoup

from ..models import Provider
from ..utils.http import HttpClient
from ..utils.time import today
from .base import Collector, CollectorResult

# SPEC §14 keyword set (lowercase, substring matched)
KEYWORDS = (
    "free tier", "free", "credit", "trial", "promotion", "promo", "student",
    "developer", "signup", "sign up", "sign-up", "$5", "$10", "$20", "token",
)


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text.lower()


class GenericCollector(Collector):
    provider_id = ""  # operates on any provider with collector == "generic"

    def __init__(self, state_path: Path) -> None:
        self.state_path = Path(state_path)

    def _load_state(self) -> dict:
        import json

        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except ValueError:
                return {}
        return {}

    def _save_state(self, state: dict) -> None:
        import json

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def collect(self, http: HttpClient, provider: Provider) -> CollectorResult:
        result = CollectorResult()
        now = today()
        state = self._load_state()
        provider_state: dict = state.get(provider.id, {})

        ok_any = False
        for url in provider.watch_urls:
            fetched = http.fetch(url)
            if fetched is None or not fetched.ok:
                result.warnings.append(
                    f"{provider.name}: watch url unreachable: {url}"
                )
                provider_state.pop(url, None)
                continue
            ok_any = True
            text = _visible_text(fetched.text)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            keywords = sorted({kw for kw in KEYWORDS if kw in text})
            previous = provider_state.get(url)
            if previous is None:
                result.notes.append(f"{provider.name}: now watching {url}")
            elif previous.get("hash") != digest:
                result.notes.append(f"{provider.name}: watch page changed: {url}")
            provider_state[url] = {
                "hash": digest,
                "keywords": keywords,
                "status": fetched.status,
                "checked": now.isoformat(),
            }

        state[provider.id] = provider_state
        self._save_state(state)
        updates: dict[str, object] = {"last_checked": now}
        if ok_any:
            updates["last_verified"] = now
        result.provider_updates = updates
        return result
