"""TokenMiner Score (SPEC §15–17) and risk tags (§35).

Pure functions over (provider, offers, models). Deterministic rules only —
no AI, no randomness, no persistence (generators recompute every run).

Weights: Free Value 30 / Model Quality 20 / Quota & Rate Limit 15 /
Context Window 10 / API Compatibility 10 / Ease of Claim 5 /
Platform Reliability 5 / Transparency 5. Grades: S 90+, A 80–89, B 70–79,
C 60–69, D <60.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Confidence, Model, Offer, Provider
from ..utils.time import days_ago

WEIGHTS = {
    "Free Value": 30,
    "Model Quality": 20,
    "Quota & Rate Limit": 15,
    "Context Window": 10,
    "API Compatibility": 10,
    "Ease of Claim": 5,
    "Platform Reliability": 5,
    "Transparency": 5,
}

_CONFIDENCE_RANK: dict[str, int] = {
    "official": 5, "high": 4, "medium": 3, "community": 1, "unknown": 0,
}


@dataclass
class ProviderScore:
    provider_id: str
    score: int
    grade: str
    components: dict[str, float]
    best_for: list[str] = field(default_factory=list)
    risk_tags: list[str] = field(default_factory=list)


def grade_for(score: int) -> str:
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def score_provider(
    provider: Provider, offers: list[Offer], models: list[Model]
) -> ProviderScore:
    """Score one provider. Offers/models are filtered to this provider
    internally, so callers cannot leak another provider's data in."""
    offers = [o for o in offers if o.provider_id == provider.id]
    models = [m for m in models if m.provider_id == provider.id]
    free_models = [m for m in models if m.free]
    live = [o for o in offers if o.status in ("active", "uncertain")]

    components = {
        "Free Value": _free_value(provider, live, free_models),
        "Model Quality": _model_quality(free_models),
        "Quota & Rate Limit": _quota(live, free_models),
        "Context Window": _context_window(free_models),
        "API Compatibility": _api_compatibility(provider),
        "Ease of Claim": _ease_of_claim(live),
        "Platform Reliability": _reliability(provider, live),
        "Transparency": _transparency(live),
    }
    score = round(sum(components.values()))
    return ProviderScore(
        provider_id=provider.id,
        score=score,
        grade=grade_for(score),
        components=components,
        best_for=_best_for(provider, live, free_models, score),
        risk_tags=_risk_tags(live, free_models),
    )


# ----------------------------------------------------------------------
def _clamp(points: float, maximum: float) -> float:
    return max(0.0, min(points, maximum))


def _free_value(provider: Provider, live: list[Offer], free_models: list[Model]) -> float:
    points = 0.0
    if free_models:
        strong = any(
            m.supports_tools or m.supports_reasoning
            or (m.context_length or 0) >= 128_000
            for m in free_models
        )
        points = 30.0 if strong else 24.0
    else:
        active = [o for o in live if o.status == "active"]
        if any(o.recurring for o in active):
            points = 22.0
        else:
            signup = [o for o in active if o.type == "signup_credit"]
            if signup:
                best = max((o.value or 0.0) for o in signup)
                points = 15.0 if best >= 10 else 12.0 if best >= 1 else 8.0
            elif any(o.type == "trial" for o in active):
                points = 6.0
    if any(o.requires_payment_method for o in live if o.requires_payment_method):
        points -= 6.0
    if provider.status == "uncertain":
        points *= 0.5
    return _clamp(points, 30.0)


def _model_quality(free_models: list[Model]) -> float:
    points = 0.0
    n = len(free_models)
    if n >= 10:
        points += 12.0
    elif n >= 5:
        points += 10.0
    elif n >= 1:
        points += 6.0
    if any(m.supports_vision for m in free_models if m.supports_vision):
        points += 4.0
    if any(m.supports_tools for m in free_models if m.supports_tools):
        points += 4.0
    return _clamp(points, 20.0)


def _quota(live: list[Offer], free_models: list[Model]) -> float:
    active = [o for o in live if o.status == "active"]
    if any(o.recurring for o in active):
        points = 10.0
    elif free_models:
        points = 8.0
    elif any(o.type == "signup_credit" for o in active):
        points = 4.0
    elif any(o.type == "trial" for o in active):
        points = 2.0
    else:
        points = 0.0
    if any(m.rate_limit for m in free_models if m.rate_limit):
        points += 5.0
    return _clamp(points, 15.0)


def _context_window(free_models: list[Model]) -> float:
    contexts = [m.context_length for m in free_models if m.context_length]
    if not contexts:
        return 2.0 if free_models else 0.0  # free models exist, size unknown
    top = max(contexts)
    if top >= 1_000_000:
        return 10.0
    if top >= 200_000:
        return 8.0
    if top >= 128_000:
        return 7.0
    if top >= 32_000:
        return 5.0
    return 3.0


def _api_compatibility(provider: Provider) -> float:
    n = len(set(provider.api_compatibility))
    if n >= 3:
        return 10.0
    if n == 2:
        return 8.0
    if n == 1:
        return 6.0
    return 0.0


def _ease_of_claim(live: list[Offer]) -> float:
    if not live:
        return 3.0  # account-only providers: just sign up
    if any(
        o.requires_payment_method is False and o.requires_phone is not True
        for o in live
    ):
        return 5.0
    if any(o.requires_phone is True for o in live):
        return 2.0
    if any(o.requires_payment_method is True for o in live):
        return 1.0
    return 3.0


def _reliability(provider: Provider, live: list[Offer]) -> float:
    points = 3.0 if provider.status == "active" else 1.0
    if any(
        o.last_verified is not None
        and (days_ago(o.last_verified) if days_ago(o.last_verified) is not None else 99) <= 7
        for o in live
    ):
        points += 2.0
    return _clamp(points, 5.0)


def _transparency(live: list[Offer]) -> float:
    if not live:
        return 0.0
    best = max(live, key=lambda o: _CONFIDENCE_RANK.get(o.confidence, 0))
    return float(_CONFIDENCE_RANK.get(best.confidence, 0))


# ----------------------------------------------------------------------
def _best_for(
    provider: Provider,
    live: list[Offer],
    free_models: list[Model],
    score: int,
) -> list[str]:
    labels: list[str] = []
    if any(m.supports_tools for m in free_models if m.supports_tools):
        labels.append("Coding")
    if any(m.supports_reasoning for m in free_models if m.supports_reasoning):
        labels.append("Reasoning")
    if any((m.context_length or 0) >= 200_000 for m in free_models):
        labels.append("Long Context")
    if any(m.supports_vision for m in free_models if m.supports_vision) or any(
        "image" in m.model_type for m in free_models
    ):
        labels.append("Multimodal")
    if score >= 5 and any(
        o.requires_payment_method is False and o.confidence in ("official", "high")
        and o.status == "active"
        for o in live
    ):
        labels.append("Beginners")
    if score >= 80 and (free_models or any(o.status == "active" for o in live)):
        labels.append("Overall Free API")
    return labels


def _risk_tags(live: list[Offer], free_models: list[Model]) -> list[str]:
    tags: list[str] = []
    if any(o.requires_payment_method for o in live if o.requires_payment_method):
        tags.append("💳 Payment Required")
    if any(o.requires_phone for o in live if o.requires_phone):
        tags.append("📱 Phone Verification")
    if any(o.requires_student_verification for o in live):
        tags.append("🎓 Student Only")
    if any(o.region_limit for o in live if o.region_limit):
        tags.append("🌍 Region Restricted")
    if any(o.end_date for o in live if o.end_date):
        tags.append("⏳ Limited Time")
    if any(o.new_users_only for o in live if o.new_users_only):
        tags.append("🎁 New Users Only")
    if any(o.recurring for o in live if o.recurring):
        tags.append("♻️ Recurring")
    if free_models or any(o.type == "free_tier" for o in live):
        tags.append("♾️ Permanent Free Tier")
    if any(
        o.confidence in ("community", "unknown") or o.stale
        for o in live
    ) and live:
        tags.append("⚠️ Unverified")
    return tags
