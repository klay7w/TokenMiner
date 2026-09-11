"""README + provider page generator tests (SPEC §18–24, §34)."""

from __future__ import annotations

from datetime import date

from tokenminer.diffing import Change
from tokenminer.generators import generate_provider_page, generate_readme
from tokenminer.models import Model, Offer, Provider
from tokenminer.scoring import score_provider

TODAY = date(2026, 9, 11)


def _data():
    providers = [
        Provider(id="goodrouter", name="GoodRouter", category="router",
                 api_compatibility=["openai", "anthropic", "gemini"],
                 status="active",
                 description="A router with free models.",
                 official_url="https://goodrouter.example",
                 signup_url="https://goodrouter.example/signup"),
        Provider(id="shady", name="ShadyCo", category="official",
                 api_compatibility=["openai"], status="active"),
    ]
    offers = [
        Offer(id="good-free", provider_id="goodrouter",
              title="Free Models Forever", type="free_tier",
              status="active", confidence="official",
              requires_payment_method=False,
              claim_url="https://goodrouter.example/free",
              source_url="https://goodrouter.example/models",
              last_verified=TODAY, last_checked=TODAY),
        Offer(id="good-credit", provider_id="goodrouter",
              title="$5 Signup Credit", type="signup_credit", value=5,
              currency="USD", status="active", confidence="official",
              new_users_only=True, claim_url="https://goodrouter.example/free",
              source_url="https://goodrouter.example/pricing",
              last_verified=TODAY),
        # community offer must NOT reach the Best Deals table (SPEC §34)
        Offer(id="shady-rumor", provider_id="shady",
              title="Reported $100 Credit", type="signup_credit", value=100,
              status="active", confidence="community",
              claim_url="https://shady.example/claim",
              source_url="https://shady.example"),
        # expired offer excluded too
        Offer(id="old", provider_id="goodrouter", title="Old Promo",
              type="promotion", status="expired", confidence="official",
              claim_url="https://goodrouter.example/old"),
    ]
    models = [
        Model(provider_id="goodrouter", model_id="dev/coder-free", free=True,
              name="Coder Free", context_length=256_000,
              supports_tools=True, supports_reasoning=True,
              model_url="https://goodrouter.example/coder",
              last_checked=TODAY),
        Model(provider_id="goodrouter", model_id="dev/small-free", free=True,
              context_length=32_000,
              model_url="https://goodrouter.example/small",
              last_checked=TODAY),
    ]
    scores = {p.id: score_provider(p, offers, models) for p in providers}
    changes = [
        Change(TODAY.isoformat(), "+", "New offer: Free Models Forever (goodrouter)"),
        Change(TODAY.isoformat(), "-", "Free model removed: dev/old-free (goodrouter)"),
    ]
    return providers, offers, models, scores, changes


def test_readme_sections_present():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    assert md.startswith("# ⛏️ TokenMiner")
    assert "Mine free AI models, API credits, tokens and developer deals." in md
    for section in (
        "# 🔥 Best Free AI Deals Right Now",
        "# 🆓 Free Models",
        "# 🎁 Free Credits",
        "# 💻 Best Free Models for Coding",
        "# 🧠 Best Free Models for Reasoning",
        "# 🕒 Recently Changed",
        "# 📖 Data & Verification",
    ):
        assert section in md, section
    assert "[LICENSE](LICENSE)" in md and "[CONTRIBUTING](CONTRIBUTING.md)" in md


def test_best_deals_table_filters_and_links():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    best = md.split("# 🔥 Best Free AI Deals Right Now")[1].split("# 🆓")[0]
    # official active offer with its claim URL is in
    assert "Free Models Forever" in best
    assert "https://goodrouter.example/free" in best
    assert "(S)" in best or "(A)" in best  # score cell rendered
    # community + expired offers filtered out (SPEC §34)
    assert "Reported $100 Credit" not in best
    assert "Old Promo" not in best


def test_free_models_table_lists_models_with_context():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    table = md.split("# 🆓 Free Models")[1].split("# 🎁")[0]
    assert "`dev/coder-free`" in table
    assert "256K" in table
    assert "https://goodrouter.example/coder" in table


def test_free_credits_section():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    credits = md.split("# 🎁 Free Credits")[1].split("# 💻")[0]
    assert "$5" in credits
    assert "New users" in credits
    assert "2026-09-11" in credits  # verified date shown (SPEC §1 Q10)
    assert "Claim](https://goodrouter.example/free)" in credits


def test_coding_reasoning_rankings_with_disclaimer():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    coding = md.split("# 💻 Best Free Models for Coding")[1].split("# 🧠")[0]
    assert "🥇" in coding and "dev/coder-free" in coding
    assert "Not a formal benchmark" in coding
    reasoning = md.split("# 🧠 Best Free Models for Reasoning")[1].split("# 🕒")[0]
    assert "Not a formal benchmark" in reasoning
    # small-free has no reasoning flag -> absent from reasoning podium
    assert "dev/small-free" not in reasoning


def test_recently_changed_section():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    recent = md.split("# 🕒 Recently Changed")[1].split("# 📖")[0]
    assert "+ New offer: Free Models Forever" in recent
    assert "- Free model removed: dev/old-free" in recent


def test_pipe_characters_escaped_in_tables():
    providers, offers, models, scores, changes = _data()
    offers.append(Offer(
        id="pipey", provider_id="shady", title="Weird | Title",
        type="trial", status="active", confidence="high",
        claim_url="https://shady.example/x", source_url="https://shady.example",
    ))
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    for line in md.splitlines():
        if line.startswith("|") and "Weird" in line:
            assert "Weird \\| Title" in line


def test_provider_page_fixed_sections():
    providers, offers, models, scores, _ = _data()
    page = generate_provider_page(providers[0], offers, models,
                                  scores["goodrouter"])
    assert page.startswith("# GoodRouter")
    for section in (
        "## Overview", "## Current Free Offers", "## Free Models", "## API",
        "## Context Windows", "## Rate Limits", "## Requirements", "## Pros",
        "## Cons", "## TokenMiner Score", "## Recommended For", "## Links",
        "## Sources", "## Last Verified",
    ):
        assert section in page, section
    assert "https://goodrouter.example/free" in page
    assert "256K" in page
    assert "2026-09-11" in page  # last verified dates (SPEC §24)


def test_provider_page_pros_cons_derived_from_data():
    providers, offers, models, scores, _ = _data()
    page = generate_provider_page(providers[0], offers, models,
                                  scores["goodrouter"])
    pros = page.split("## Pros")[1].split("## Cons")[0]
    assert "free model(s) available" in pros
    assert "tool calling" in pros
    cons = page.split("## Cons")[1].split("## TokenMiner Score")[0]
    # new_users_only signup credit -> no 'card' con; page must not invent one
    assert "payment method required" not in cons
