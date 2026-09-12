"""README + provider page generator tests (SPEC §18–24, §34)."""

from __future__ import annotations

import re
from pathlib import Path

from tokenminer.diffing import Change
from tokenminer.generators import generate_provider_page, generate_readme
from tokenminer.models import Model, Offer, Provider
from tokenminer.scoring import score_provider
from tokenminer.utils.time import today

# Rule: no absolute dates in tests — TODAY is always the real current UTC date.
TODAY = today()

ROOT = Path(__file__).resolve().parents[1]

# Combined modality + capability legend closing both ranking sections.
_RANKING_LEGEND = (
    "*📝 text · 🖼️ image I/O · 👁️ image input (vision)"
    " · 🎬 video · 🔊 audio · 🧩 embedding · 🛠️ tools · 🧠 reasoning*"
)

# Width audit: GitHub's content area is ~1012px (~110 chars). Table rows are
# measured after stripping rendered-invisible markup (link URLs, <img> tags).
_MAX_TABLE_ROW_WIDTH = 110
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_IMG_RE = re.compile(r"<img\b[^>]*>")


def _assert_table_width(md: str, label: str) -> None:
    for line in md.splitlines():
        if not line.startswith("|"):
            continue
        visible = _LINK_RE.sub(r"\1", _IMG_RE.sub("", line))
        assert len(visible) <= _MAX_TABLE_ROW_WIDTH, (
            f"{label}: table row {len(visible)} > {_MAX_TABLE_ROW_WIDTH} chars: {visible!r}"
        )


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
    assert "| # | Provider | Deal | Best Model | Ctx | Score | Get |" in best
    # official active offer: compact deal label + claim URL link
    assert "2 free models ♾️" in best
    assert "[→](https://goodrouter.example/free)" in best
    # provider cell: favicon + link to provider page
    assert "s2/favicons?domain=goodrouter.example" in best
    assert "[GoodRouter](docs/providers/goodrouter.md)" in best
    # best free model by context, linked, short name + K/M context
    assert "[Coder Free](https://goodrouter.example/coder)" in best
    assert "| 256K |" in best
    assert re.search(r"\| \d{1,3} [SABCD] \|", best)  # "89 A" style score cell
    # community + expired offers filtered out (SPEC §34)
    assert "Reported $100 Credit" not in best
    assert "Old Promo" not in best


def test_free_models_table_lists_models_with_context():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    table = md.split("# 🆓 Free Models")[1].split("# 🎁")[0]
    assert "| Provider | Model | Ctx | Caps | Link |" in table
    assert "Coder Free" in table  # compact display name, raw id replaced
    assert "256K" in table
    assert "https://goodrouter.example/coder" in table  # ↗ link column
    assert "📝" in table  # modality icons
    # rate limit / API columns replaced by one footnote line
    assert (
        "Rate limits are rarely published; see provider pages. "
        "API compatibility: GoodRouter — openai/anthropic/gemini." in table
    )
    # legend under the iconized table
    assert "📝 text · 🖼️ image · 🎬 video · 🔊 audio · 🧩 embedding" in table


def test_free_models_table_keeps_all_rows():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    table = md.split("# 🆓 Free Models")[1].split("# 🎁")[0]
    # Free Models table keeps ALL rows (no rate-limit column truncation)
    assert sum(1 for ln in table.splitlines() if ln.startswith("|") and "Coder Free" in ln) == 1
    assert sum(1 for ln in table.splitlines() if ln.startswith("|") and "small-free" in ln) == 1


def test_free_credits_section():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    credits = md.split("# 🎁 Free Credits")[1].split("# 💻")[0]
    assert "| Provider | Amount | Requirement | Verified | Claim |" in credits
    assert "$5 once" in credits
    assert "New users" in credits
    assert TODAY.isoformat() in credits  # verified date shown (SPEC §1 Q10)
    assert "Claim](https://goodrouter.example/free)" in credits


def test_coding_reasoning_rankings_with_disclaimer():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    coding = md.split("# 💻 Best Free Models for Coding")[1].split("# 🧠")[0]
    # podium line: bold-linked model name, ctx, capability icons, provider name
    assert (
        "🥇 **[Coder Free](https://goodrouter.example/coder)**"
        " · 256K ctx · 📝🛠️🧠 · GoodRouter"
    ) in coding
    assert "Not a formal benchmark" in coding
    assert "<details>" not in coding  # single candidate -> podium only
    reasoning = md.split("# 🧠 Best Free Models for Reasoning")[1].split("# 🕒")[0]
    assert "Not a formal benchmark" in reasoning
    # small-free has no reasoning flag -> absent from reasoning podium
    assert "small-free" not in reasoning
    assert "<details>" not in reasoning
    # podium-only sections still close with the combined icon legend
    for section, label in ((coding, "coding"), (reasoning, "reasoning")):
        body = section.splitlines()
        assert sum(1 for ln in body if ln == _RANKING_LEGEND) == 1, label
        assert body[-2] == _RANKING_LEGEND and body[-1] == "", label


def _add_tool_models(models: list[Model], provider_id: str, count: int) -> None:
    for i in range(count):
        models.append(Model(
            provider_id=provider_id, model_id=f"tool-{i}", free=True,
            context_length=100_000 - i * 10_000,
            supports_tools=True,
            model_url=f"https://openrouter.example/tool-{i}",
            last_checked=TODAY,
        ))


def test_coding_ranking_details_block_when_more_than_three():
    providers, offers, models, scores, changes = _data()
    providers.append(Provider(
        id="openrouter", name="OpenRouter", category="router", status="active",
    ))
    _add_tool_models(models, "openrouter", 5)
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    coding = md.split("# 💻 Best Free Models for Coding")[1].split("# 🧠")[0]
    # podium stays sorted by context desc (Coder Free 256K first)
    assert "🥇 **[Coder Free]" in coding
    assert "🥈 **[tool-0](https://openrouter.example/tool-0)** · 100K ctx · 📝🛠️ · OpenRouter" in coding
    assert "🥉 **[tool-1](https://openrouter.example/tool-1)** · 90K ctx · 📝🛠️ · OpenRouter" in coding
    # remaining models collapse into a details block with the correct count
    assert "<details>" in coding and "</details>" in coding
    assert "<summary><b>More tool-calling free models (3)</b></summary>" in coding
    assert "- [tool-2](https://openrouter.example/tool-2) — 80K" in coding
    assert "- [tool-3](https://openrouter.example/tool-3) — 70K" in coding
    assert "- [tool-4](https://openrouter.example/tool-4) — 60K" in coding
    # blank lines required for markdown rendering inside <details>
    body = coding.splitlines()
    summary = body.index("<summary><b>More tool-calling free models (3)</b></summary>")
    assert body[summary - 1] == "<details>"
    assert body[summary + 1] == ""
    assert body[summary + 2].startswith("- ")
    # legend comes after the details block (blank line keeps it outside it)
    assert body[-4] == "</details>" and body[-3] == ""
    assert body[-2] == _RANKING_LEGEND and body[-1] == ""


def test_ranking_legend_absent_without_podium():
    """No candidates -> placeholder only, no icon legend line."""
    providers, offers, models, scores, changes = _data()
    models = [m for m in models if not (m.supports_tools or m.supports_reasoning)]
    scores = {p.id: score_provider(p, offers, models) for p in providers}
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    coding = md.split("# 💻 Best Free Models for Coding")[1].split("# 🧠")[0]
    reasoning = md.split("# 🧠 Best Free Models for Reasoning")[1].split("# 🕒")[0]
    for section, label in ((coding, "coding"), (reasoning, "reasoning")):
        assert "_No free models with confirmed support right now._" in section, label
        assert _RANKING_LEGEND not in section, label
        assert "🛠️ tools" not in section, label


def test_podium_lines_hard_broken_and_consecutive():
    """Podium lines are one tight paragraph hard-broken per medal ("<br>")."""

    def _assert_podium(section: str, label: str) -> None:
        body = section.splitlines()
        podium = [i for i, ln in enumerate(body)
                  if ln.startswith(("🥇", "🥈", "🥉"))]
        assert podium, f"{label}: no podium lines"
        # consecutive block: no blank lines between podium lines
        assert podium == list(range(podium[0], podium[0] + len(podium))), podium
        # every podium line except the last ends with a hard break
        for i in podium[:-1]:
            assert body[i].endswith("<br>"), (
                f"{label}: {body[i]!r} missing '<br>'"
            )
        assert not body[podium[-1]].endswith("<br>"), (
            f"{label}: last podium line must not end with '<br>': {body[podium[-1]]!r}"
        )
        # no line uses the old trailing-"\" hard break anywhere in the block
        for ln in body:
            assert not ln.endswith("\\"), f"{label}: {ln!r} ends with '\\'"

    # >3 candidates: 3-line podium followed by a <details> block
    providers, offers, models, scores, changes = _data()
    providers.append(Provider(
        id="openrouter", name="OpenRouter", category="router", status="active",
    ))
    _add_tool_models(models, "openrouter", 5)
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    coding = md.split("# 💻 Best Free Models for Coding")[1].split("# 🧠")[0]
    _assert_podium(coding, "coding podium (3 + details)")

    # three candidates, podium only (no details block)
    providers, offers, models, scores, changes = _data()
    providers.append(Provider(
        id="openrouter", name="OpenRouter", category="router", status="active",
    ))
    for i in range(2):
        models.append(Model(
            provider_id="openrouter", model_id=f"think-{i}", free=True,
            context_length=100_000 - i * 10_000,
            supports_reasoning=True,
            model_url=f"https://openrouter.example/think-{i}",
            last_checked=TODAY,
        ))
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    reasoning = md.split("# 🧠 Best Free Models for Reasoning")[1].split("# 🕒")[0]
    _assert_podium(reasoning, "reasoning podium (3, podium only)")

    # single candidate: the one podium line is the last -> no hard break
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    reasoning = md.split("# 🧠 Best Free Models for Reasoning")[1].split("# 🕒")[0]
    _assert_podium(reasoning, "reasoning podium (single candidate)")


def test_ranking_podium_only_when_three_or_fewer():
    providers, offers, models, scores, changes = _data()
    providers.append(Provider(
        id="openrouter", name="OpenRouter", category="router", status="active",
    ))
    # two extra reasoning models -> reasoning podium of 3, no details block
    for i in range(2):
        models.append(Model(
            provider_id="openrouter", model_id=f"think-{i}", free=True,
            context_length=100_000 - i * 10_000,
            supports_reasoning=True,
            model_url=f"https://openrouter.example/think-{i}",
            last_checked=TODAY,
        ))
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    reasoning = md.split("# 🧠 Best Free Models for Reasoning")[1].split("# 🕒")[0]
    assert "🥇 **[Coder Free](https://goodrouter.example/coder)** · 256K ctx · 📝🛠️🧠 · GoodRouter" in reasoning
    assert "🥈 **[think-0](https://openrouter.example/think-0)** · 100K ctx · 📝🧠 · OpenRouter" in reasoning
    assert "🥉 **[think-1](https://openrouter.example/think-1)** · 90K ctx · 📝🧠 · OpenRouter" in reasoning
    assert "<details>" not in reasoning


def test_recently_changed_section():
    providers, offers, models, scores, changes = _data()
    md = generate_readme(providers, offers, models, scores, changes, TODAY)
    body = md.split("# 🕒 Recently Changed")[1].split("# 📖")[0]
    lines = [l for l in body.splitlines() if l.strip()]
    # Date-prefixed entry lines, no markdown bullet, no +/-/⚠ symbol.
    # All entry lines except the last end with a literal <br> hard break,
    # so GitHub keeps each entry on its own line. A trailing "\\" would be
    # absorbed into an autolinked URL when the entry ends with one.
    first = f"{TODAY.isoformat()}: New offer: Free Models Forever (goodrouter)<br>"
    second = f"{TODAY.isoformat()}: Free model removed: dev/old-free (goodrouter)"
    tail = "Full history in [CHANGELOG.md](CHANGELOG.md)."
    assert lines[:2] == [first, second]
    assert lines[-1] == tail
    for line in lines:
        assert not line.endswith("\\"), f"line must not end with '\\': {line!r}"
    for line in lines[:-2]:
        assert not line.lstrip().startswith("-")  # no markdown bullet


def test_pipe_characters_escaped_in_tables():
    providers, offers, models, scores, changes = _data()
    offers.append(Offer(
        id="pipey", provider_id="shady", title="Weird | Title",
        type="promotion", status="active", confidence="high",
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
    assert page.splitlines()[0].startswith("# ")
    assert "GoodRouter" in page.splitlines()[0]
    assert "s2/favicons?domain=goodrouter.example" in page.splitlines()[0]
    for section in (
        "## Overview", "## Current Free Offers", "## Free Models", "## API",
        "## Context Windows", "## Rate Limits", "## Requirements", "## Pros",
        "## Cons", "## TokenMiner Score", "## Recommended For", "## Links",
        "## Sources", "## Last Verified",
    ):
        assert section in page, section
    assert "| Model | Ctx | Caps | Link |" in page
    assert "Coder Free" in page
    assert "🛠️" in page and "🧠" in page  # capability icons
    assert "🖼️ image I/O · 👁️ image input (vision)" in page  # legend
    assert "🛠️ tools · 🧠 reasoning" in page
    assert "https://goodrouter.example/free" in page
    assert "256K" in page
    assert TODAY.isoformat() in page  # last verified dates (SPEC §24)


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


def test_width_audit_fixture_outputs():
    """Every table row in generated README + provider pages fits GitHub width."""
    providers, offers, models, scores, changes = _data()
    readme = generate_readme(providers, offers, models, scores, changes, TODAY)
    _assert_table_width(readme, "generated README")
    for provider in providers[:2]:
        page = generate_provider_page(
            provider, offers, models, scores[provider.id]
        )
        _assert_table_width(page, f"generated page {provider.id}")


def test_width_audit_committed_docs():
    """Guard against regression: committed README + provider pages stay compact."""
    readme_path = ROOT / "README.md"
    if readme_path.exists():
        _assert_table_width(
            readme_path.read_text(encoding="utf-8"), "README.md"
        )
    pages_dir = ROOT / "docs" / "providers"
    pages = sorted(pages_dir.glob("*.md")) if pages_dir.exists() else []
    assert len(pages) >= 2, "expected at least 2 committed provider pages"
    for page in pages:
        _assert_table_width(
            page.read_text(encoding="utf-8"), f"docs/providers/{page.name}"
        )
