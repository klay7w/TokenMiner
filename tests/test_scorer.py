"""Scorer tests (SPEC §15–17, §35): exact scores, full decomposition, labels."""

from __future__ import annotations

from datetime import date, timedelta

from tokenminer.models import Model, Offer, Provider
from tokenminer.scoring.scorer import WEIGHTS, grade_for, score_provider

TODAY = date(2026, 9, 11)


def _provider(**kw) -> Provider:
    base = dict(id="test", name="Test", category="router", status="active",
                api_compatibility=["openai", "anthropic", "gemini"])
    base.update(kw)
    return Provider(**base)


def _offer(**kw) -> Offer:
    base = dict(id="o1", provider_id="test", title="Offer", type="free_tier",
                status="active", confidence="official",
                requires_payment_method=False, last_verified=TODAY)
    base.update(kw)
    return Offer(**base)


def _model(**kw) -> Model:
    base = dict(provider_id="test", model_id="m", free=True,
                context_length=200_000, supports_tools=True,
                supports_vision=True, supports_reasoning=True,
                rate_limit="30 RPM", last_checked=TODAY)
    base.update(kw)
    return Model(**base)


def test_only_this_providers_offers_and_models_count():
    """Another provider's offers/models must not leak into the score."""
    provider = _provider()
    foreign_offer = _offer(id="foreign", provider_id="other",
                           type="signup_credit", value=100,
                           requires_payment_method=True,
                           requires_student_verification=True)
    foreign_model = _model(provider_id="other", model_id="foreign")
    score = score_provider(provider, [foreign_offer], [foreign_model])
    # nothing of this provider's -> near-zero free value, no penalties
    assert score.components["Free Value"] == 0.0
    assert "💳 Payment Required" not in score.risk_tags
    assert "🎓 Student Only" not in score.risk_tags


def test_full_100_point_decomposition():
    """A provider with every strong signal must sum to exactly 100 (grade S)."""
    provider = _provider()
    offer = _offer(recurring=True)  # recurring + rate limits -> full quota
    models = [_model(model_id=f"m{i}", context_length=1_000_000)
              for i in range(12)]
    score = score_provider(provider, [offer], models)
    assert score.components == {
        "Free Value": 30.0,
        "Model Quality": 20.0,
        "Quota & Rate Limit": 15.0,
        "Context Window": 10.0,
        "API Compatibility": 10.0,
        "Ease of Claim": 5.0,
        "Platform Reliability": 5.0,
        "Transparency": 5.0,
    }
    assert score.score == 100
    assert score.grade == "S"
    assert sum(WEIGHTS.values()) == 100


def test_signup_credit_only_provider():
    provider = _provider(api_compatibility=["openai"])
    offer = _offer(type="signup_credit", value=5, recurring=False)
    score = score_provider(provider, [offer], [])
    # FreeValue 12 (signup <10$) + Quota 4 + API 6 + Ease 5 + Reliability 5
    # + Transparency 5 = 37 -> D
    assert score.components["Free Value"] == 12.0
    assert score.score == 37
    assert score.grade == "D"


def test_uncertain_provider_halves_free_value():
    provider = _provider(status="uncertain")
    # weak free model: no tools/reasoning, context < 128k -> base 24
    models = [_model(model_id="m", supports_tools=None,
                     supports_reasoning=None, context_length=32_000)]
    score = score_provider(provider, [], models)
    assert score.components["Free Value"] == 12.0  # 24 * 0.5
    # strong free model (tools) would be 30 * 0.5 = 15
    strong = score_provider(_provider(status="uncertain"), [], [_model()])
    assert strong.components["Free Value"] == 15.0
    assert "⚠️ Unverified" not in score.risk_tags  # no offers -> no tag


def test_payment_method_penalty():
    provider = _provider()
    offer = _offer(type="signup_credit", value=25,
                   requires_payment_method=True)
    score = score_provider(provider, [offer], [])
    # 15 (signup >= 10) - 6 (card) = 9
    assert score.components["Free Value"] == 9.0
    assert "💳 Payment Required" in score.risk_tags


def test_grades():
    assert [grade_for(s) for s in (100, 90, 89, 80, 79, 70, 69, 60, 59, 0)] == [
        "S", "S", "A", "A", "B", "B", "C", "C", "D", "D",
    ]


def test_best_for_labels():
    provider = _provider()
    offer = _offer()
    models = [_model(context_length=250_000)]
    score = score_provider(provider, [offer], models)
    for label in ("Coding", "Reasoning", "Long Context", "Multimodal",
                  "Beginners"):
        assert label in score.best_for
    # score is high + free models -> Overall Free API
    assert "Overall Free API" in score.best_for


def test_best_for_requires_evidence():
    provider = _provider()
    score = score_provider(provider, [], [])  # nothing at all
    assert score.best_for == []


def test_risk_tags():
    provider = _provider()
    offers = [
        _offer(id="a", new_users_only=True),
        _offer(id="b", recurring=True),
        _offer(id="c", end_date=TODAY + timedelta(days=3)),
        _offer(id="d", region_limit="US only"),
    ]
    score = score_provider(provider, offers, [])
    for tag in ("🎁 New Users Only", "♻️ Recurring", "⏳ Limited Time",
                "🌍 Region Restricted", "♾️ Permanent Free Tier"):
        assert tag in score.risk_tags


def test_stale_offer_gets_unverified_tag():
    provider = _provider()
    offer = _offer(stale=True)
    score = score_provider(provider, [offer], [])
    assert "⚠️ Unverified" in score.risk_tags


def test_context_window_tiers():
    def top_ctx(ctx: int | None) -> float:
        provider = _provider()
        models = [_model(context_length=ctx)]
        return score_provider(provider, [], models).components["Context Window"]

    assert top_ctx(1_500_000) == 10.0
    assert top_ctx(200_000) == 8.0
    assert top_ctx(128_000) == 7.0
    assert top_ctx(32_000) == 5.0
    assert top_ctx(8_000) == 3.0
    assert top_ctx(None) == 2.0  # free models exist, size unknown


def test_quota_tiers():
    provider = _provider()
    # recurring credits, no rate info
    s = score_provider(provider, [_offer(recurring=True)], [])
    assert s.components["Quota & Rate Limit"] == 10.0
    # free models with published rate limits
    s = score_provider(provider, [], [_model()])
    assert s.components["Quota & Rate Limit"] == 13.0
    # nothing
    s = score_provider(provider, [], [])
    assert s.components["Quota & Rate Limit"] == 0.0


def test_transparency_ranks_confidence():
    provider = _provider()
    for confidence, expected in (
        ("official", 5.0), ("high", 4.0), ("medium", 3.0),
        ("community", 1.0), ("unknown", 0.0),
    ):
        offer = _offer(confidence=confidence)
        s = score_provider(provider, [offer], [])
        assert s.components["Transparency"] == expected
