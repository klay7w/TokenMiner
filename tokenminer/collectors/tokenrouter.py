"""TokenRouter collector (SPEC §13).

Parses the server-rendered https://tokenrouter.com/models page (the API at
api.tokenrouter.com requires auth and is not used). The models page carries
model id / provider / capabilities / API formats but NO context or pricing
numbers — those fields stay null (never guessed). Free models carry a
``-free`` suffix. Signup-credit evidence is re-scanned every run from
/docs and /blog; an offer is only recorded when an official page actually
states it.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..models import Model, Offer
from ..utils.http import HttpClient
from ..utils.time import today
from .base import Collector, CollectorResult

MODELS_URL = "https://tokenrouter.com/models"
DOCS_URL = "https://tokenrouter.com/docs"
BLOG_URL = "https://tokenrouter.com/blog"
FREE_OFFER_ID = "tokenrouter-free-models"

_CAPABILITY_MAP = {
    "text": "text",
    "image": "image",
    "video": "video",
    "embedding": "embedding",
    "audio": "audio",
}

# credit/promotion evidence keywords for /docs and /blog scans
CREDIT_KEYWORDS = (
    "credit", "credits", "signup credit", "sign-up credit", "promotion",
    "promo code", "free tier", "free credits",
)


class TokenRouterCollector(Collector):
    provider_id = "tokenrouter"

    def collect(self, http: HttpClient, provider) -> CollectorResult:  # type: ignore[override]
        result = CollectorResult()
        now = today()
        html = http.get_text(MODELS_URL)
        if not html:
            result.warnings.append("TokenRouter: models page unreachable")
            return result
        models = self._parse_models(html, now)
        if not models:
            result.warnings.append("TokenRouter: no models parsed (page layout changed?)")
            return result

        free_models = [m for m in models if m.free]
        result.models = models
        result.provider_updates = {
            "status": "active",
            "last_checked": now,
            "last_verified": now,
        }
        if free_models:
            n = len(free_models)
            result.offers = [Offer(
                id=FREE_OFFER_ID,
                provider_id=self.provider_id,
                title=f"TokenRouter Free Models ({n} model{'s' if n != 1 else ''})",
                type="free_tier",
                description=(
                    f"{n} model{'s' if n != 1 else ''} with '-free' suffix in "
                    f"the id (e.g. {free_models[0].model_id}) listed on the "
                    f"official models page. Context length and pricing are not "
                    f"published on that page and remain unknown."
                ),
                recurring=False,
                new_users_only=False,
                requires_payment_method=False,
                claim_url=MODELS_URL,
                source_url=MODELS_URL,
                status="active",
                confidence="official",
                last_checked=now,
                last_verified=now,
            )]

        # Re-scan official docs/blog for signup-credit / promotion evidence.
        scanned = []
        for url in (DOCS_URL, BLOG_URL):
            text = http.get_text(url)
            if text is None:
                scanned.append(f"{url}: unreachable")
                continue
            soup = BeautifulSoup(text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            page_text = soup.get_text(" ", strip=True).lower()
            found = [kw for kw in CREDIT_KEYWORDS if kw in page_text]
            scanned.append(
                f"{url}: {'credit evidence keywords: ' + ', '.join(found) if found else 'no credit/promotion evidence'}"
            )
        result.notes.extend(scanned)
        return result

    def _parse_models(self, html: str, checked: object) -> list[Model]:
        soup = BeautifulSoup(html, "html.parser")
        models: list[Model] = []
        for card in soup.select("li.tr-seo-card"):
            link = card.find("h2").find("a") if card.find("h2") else None
            if link is None:
                continue
            model_id = link.get_text(strip=True)
            if not model_id:
                continue
            href = link.get("href") or ""
            provider_name = ""
            capabilities: list[str] = []
            for p in card.find_all("p"):
                text = p.get_text(" ", strip=True)
                if text.startswith("Provider:"):
                    provider_name = text.split(":", 1)[1].strip()
                elif text.startswith("Capabilities:"):
                    capabilities = [
                        _CAPABILITY_MAP.get(c.strip().lower(), c.strip().lower())
                        for c in text.split(":", 1)[1].split("|")
                    ]
            seen: list[str] = []
            for c in capabilities:
                if c and c not in seen:
                    seen.append(c)
            models.append(Model(
                provider_id=self.provider_id,
                model_id=model_id,
                name=model_id,
                developer=provider_name or model_id.split("/", 1)[0],
                model_type=seen or ["text"],
                context_length=None,   # not published on the models page
                max_output_tokens=None,
                input_price=None,
                output_price=None,
                free=model_id.endswith("-free"),
                rate_limit=None,
                supports_tools=None,     # unknown — page does not say
                supports_vision=None,
                supports_reasoning=None,
                model_url=f"https://tokenrouter.com{href}" if href.startswith("/") else (href or MODELS_URL),
                source_url=MODELS_URL,
                last_checked=checked,
                last_verified=checked,
            ))
        return models
