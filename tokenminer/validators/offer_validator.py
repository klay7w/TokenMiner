"""Offer re-verification (SPEC §33, §25–26).

For every offer with status active/uncertain: GET claim_url and source_url
(2xx after redirects = reachable), scan the source text for free keywords,
scan for expired signals, check end_date. ``last_checked`` is always bumped;
``last_verified`` only when everything checks out. Stale: >7 days since last
verified -> stale flag; >30 days -> status uncertain. Never auto-expire from
staleness alone.
"""

from __future__ import annotations

import re

from ..models import Offer
from ..utils.http import HttpClient
from ..utils.time import days_ago, today

FREE_KEYWORDS = (
    r"\bfree\b", r"\bcredits?\b", r"\btrial\b", r"\bpromot\w+",
    r"\bsign-?up\b", r"no cost",
)
EXPIRED_SIGNALS = (
    r"\bexpired\b", r"\bhas ended\b", r"\bended\b",
    r"\bno longer available\b", r"\bhas closed\b", r"\bdiscontinued\b",
)
STALE_DAYS = 7
UNCERTAIN_DAYS = 30


def _has_keyword(text: str, patterns: tuple[str, ...]) -> str | None:
    lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, lower):
            return pattern
    return None


def _expired_sentence(text: str) -> str | None:
    """A sentence that mentions BOTH a deal and an expired signal.

    A lone 'ended'/'expired' elsewhere on the page (e.g. inside unrelated
    docs prose) is not an obvious expiration (SPEC §33: 明显 expired 信息).
    """
    for sentence in re.split(r"(?<=[.!?])\s+", text.lower()):
        if _has_keyword(sentence, EXPIRED_SIGNALS) and _has_keyword(
            sentence, FREE_KEYWORDS + (r"\boffer\b", r"\bdeal\b")
        ):
            return sentence.strip()
    return None


class OfferValidator:
    """Re-checks offers against their official sources."""

    def validate_offers(
        self, offers: list[Offer], http: HttpClient
    ) -> tuple[list[Offer], list[str]]:
        now = today()
        warnings: list[str] = []
        for offer in offers:
            if offer.status in ("expired", "unavailable"):
                offer.last_checked = now
                self._apply_staleness(offer, now)
                continue
            self._validate_one(offer, http, now, warnings)
            self._apply_staleness(offer, now)
        return offers, warnings

    def _validate_one(
        self, offer: Offer, http: HttpClient, now, warnings: list[str]
    ) -> None:
        offer.last_checked = now

        claim = http.fetch(offer.claim_url) if offer.claim_url else None
        source = http.fetch(offer.source_url) if offer.source_url else None

        if source is None or not source.ok:
            warnings.append(f"{offer.id}: source unreachable: {offer.source_url}")
        if offer.claim_url and (claim is None or not claim.ok):
            warnings.append(f"{offer.id}: claim unreachable: {offer.claim_url}")

        text = " ".join(
            r.text for r in (source, claim) if r is not None and r.ok
        )
        keyword = _has_keyword(text, FREE_KEYWORDS) if text else None
        expired_sentence = _expired_sentence(text) if text else None
        end_passed = offer.end_date is not None and offer.end_date < now

        if end_passed or expired_sentence:
            offer.status = "expired"
            if expired_sentence:
                warnings.append(
                    f"{offer.id}: expired signal on source: '{expired_sentence}'"
                )
            return

        source_ok = source is not None and source.ok
        if source_ok and keyword is not None:
            offer.last_verified = now
        else:
            warnings.append(
                f"{offer.id}: not verified this run "
                f"(source_ok={source_ok}, free_keyword={keyword})"
            )

    def _apply_staleness(self, offer: Offer, now) -> None:
        age = days_ago(offer.last_verified)
        offer.stale = age is not None and age > STALE_DAYS
        if age is not None and age > UNCERTAIN_DAYS and offer.status == "active":
            offer.status = "uncertain"  # staleness alone never expires an offer
