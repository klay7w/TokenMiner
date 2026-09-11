"""Unit tests for the shared table-formatting helpers (generators/format.py)."""

from __future__ import annotations

from datetime import date

from tokenminer.generators.format import (
    caps_icons,
    caps_with_capabilities,
    ctx_short,
    credit_amount,
    deal_short,
    favicon_domain,
    legend_line,
    model_short,
    provider_cell,
    requirement_short,
)
from tokenminer.models import Model, Offer, Provider

TODAY = date(2026, 9, 11)


def _provider(**kwargs) -> Provider:
    defaults = dict(id="acme", name="Acme AI", official_url="https://www.acme.example/api")
    defaults.update(kwargs)
    return Provider(**defaults)


def _model(**kwargs) -> Model:
    defaults = dict(provider_id="acme", model_id="acme/big-model", free=True)
    defaults.update(kwargs)
    return Model(**defaults)


def _offer(**kwargs) -> Offer:
    defaults = dict(id="o", provider_id="acme", title="Deal", type="signup_credit")
    defaults.update(kwargs)
    return Offer(**defaults)


# ---------------------------------------------------------------- favicon
def test_favicon_domain_strips_www():
    assert favicon_domain(_provider()) == "acme.example"


def test_favicon_domain_missing_url():
    assert favicon_domain(_provider(official_url=None)) is None


def test_provider_cell_with_logo_and_link():
    cell = provider_cell(_provider())
    assert cell == (
        '<img src="https://www.google.com/s2/favicons?domain=acme.example&sz=32" '
        'width="16" valign="middle"> [Acme AI](docs/providers/acme.md)'
    )


def test_provider_cell_without_official_url_is_name_only():
    cell = provider_cell(_provider(official_url=None))
    assert "favicons" not in cell
    assert "[Acme AI](docs/providers/acme.md)" in cell


# ---------------------------------------------------------------- ctx_short
def test_ctx_short():
    assert ctx_short(1_000_000) == "1M"
    assert ctx_short(1_048_576) == "1M"
    assert ctx_short(262_144) == "262K"
    assert ctx_short(66_000) == "66K"
    assert ctx_short(None) == "—"
    assert ctx_short(512) == "512"


# ---------------------------------------------------------------- model_short
def test_model_short_strips_free_suffix():
    m = _model(name="Inkling Small (free)", developer="thinkingmachines")
    assert model_short(m) == "Inkling Small"


def test_model_short_strips_developer_prefix():
    m = _model(name="OpenAI: gpt-oss-20b", developer="openai")
    assert model_short(m) == "gpt-oss-20b"


def test_model_short_keeps_mismatched_prefix():
    m = _model(name="Z.ai: GLM 5.3", developer="z-ai")
    assert model_short(m) == "Z.ai: GLM 5.3"  # "z.ai" != "z-ai" -> kept


def test_model_short_tokenrouter_id_case():
    m = _model(model_id="z-ai/glm-5.3-free", name="z-ai/glm-5.3-free")
    assert model_short(m) == "glm-5.3-free"


def test_model_short_fallback_to_model_id():
    m = _model(model_id="dev/small-free", name="")
    assert model_short(m) == "dev/small-free"
    assert model_short(m) != ""


# ---------------------------------------------------------------- caps icons
def test_caps_icons_ordered_modality_icons():
    m = _model(model_type=["audio", "text", "image"])
    assert caps_icons(m) == "📝🖼️🔊"
    assert caps_icons(_model(model_type=["embedding"])) == "🧩"
    assert caps_icons(_model(model_type=["video", "embedding"])) == "🎬🧩"


def test_caps_with_capabilities():
    m = _model(model_type=["text", "image"], supports_tools=True,
               supports_vision=False, supports_reasoning=True)
    assert caps_with_capabilities(m) == "📝🖼️🛠️🧠"


def test_legend_line():
    assert legend_line() == "*📝 text · 🖼️ image · 🎬 video · 🔊 audio · 🧩 embedding*"
    assert legend_line(capabilities=True) == (
        "*📝 text · 🖼️ image I/O · 👁️ image input (vision)"
        " · 🎬 video · 🔊 audio · 🧩 embedding · 🛠️ tools · 🧠 reasoning*"
    )


# ---------------------------------------------------------------- deal_short
def test_deal_short_free_tier_with_models():
    o = _offer(type="free_tier")
    assert deal_short(o, 19) == "19 free models ♾️"


def test_deal_short_free_tier_without_models():
    o = _offer(type="free_tier")
    assert deal_short(o, 0) == "Free tier ♾️"


def test_deal_short_recurring():
    o = _offer(type="recurring_credit", value=10, currency="USD", recurring=True)
    assert deal_short(o, 0) == "$10/mo ♻️"


def test_deal_short_signup_credit_new_users():
    o = _offer(type="signup_credit", value=5, currency="USD", new_users_only=True)
    assert deal_short(o, 0) == "$5 credit 🎁"


def test_deal_short_trial():
    assert deal_short(_offer(type="trial"), 0) == "Trial ⏳"


def test_deal_short_student_recurring():
    o = _offer(type="student", value=5.99, currency="USD", recurring=True)
    assert deal_short(o, 0) == "$5.99/mo 🎓"


def test_deal_short_non_usd_currency():
    o = _offer(type="signup_credit", value=5.99, currency="EUR")
    assert deal_short(o, 0) == "5.99 USD credit"


def test_deal_short_card_and_end_date_suffix():
    o = _offer(type="student", value=5.99, currency="USD", recurring=True,
               requires_payment_method=True, end_date=date(2026, 9, 30))
    assert deal_short(o, 0) == "$5.99/mo 🎓 💳 ⏳09-30"


# ---------------------------------------------------------------- credits
def test_credit_amount_variants():
    assert credit_amount(_offer(value=5, currency="USD")) == "$5 once"
    assert credit_amount(
        _offer(type="recurring_credit", value=10, currency="USD", recurring=True)
    ) == "$10/mo ♻️"
    assert credit_amount(
        _offer(value=20, currency="USD", end_date=date(2026, 9, 30))
    ) == "⏳ 09-30 $20 once"


def test_requirement_short_variants():
    assert requirement_short(_offer(new_users_only=True)) == "New users"
    assert requirement_short(_offer()) == "Account"
    assert requirement_short(_offer(
        requires_student_verification=True, requires_payment_method=True
    )) == "🎓 Student · 💳 Card"
