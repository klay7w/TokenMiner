"""README.md generator (SPEC §18–23). Pure f-strings — no template engine.

Tables are kept compact (favicon provider cells, icon caps, K/M context,
footnotes instead of extra columns) so every row fits GitHub's ~1012px
content area without horizontal scroll.
"""

from __future__ import annotations

from datetime import date

from ..diffing import Change
from ..models import Model, Offer, Provider
from ..scoring.scorer import ProviderScore
from ..utils.time import to_iso
from .format import (
    caps_icons,
    caps_with_capabilities,
    ctx_short,
    credit_amount,
    deal_short,
    esc,
    legend_line,
    model_short,
    provider_cell,
    requirement_short,
)

SUBTITLE = "Mine free AI models, API credits, tokens and developer deals."


def _best_free_model(models: list[Model]) -> Model | None:
    if not models:
        return None
    return sorted(
        models,
        key=lambda m: (
            -(m.context_length or 0),
            not m.supports_tools,
            not m.supports_reasoning,
            m.model_id,
        ),
    )[0]


def _podium_and_details(
    lines: list[str],
    candidates: list[Model],
    providers_by_id: dict[str, Provider],
    details_label: str,
) -> None:
    """§22 ranking block: top-3 podium lines + collapsible list for the rest.

    Podium lines are bold model links; remaining models collapse into one
    <details> block (blank lines around the body are required so GitHub
    renders markdown inside <details>). Three or fewer candidates render
    podium-only, without a details block.

    Every section that shows a podium closes with one italic legend line
    explaining the modality + capability icons (shared legend_line with
    capabilities=True); a blank line before it keeps it outside the
    <details> HTML block when one is present.

    Podium lines stay one tight markdown paragraph, so every line except
    the last ends with a GFM hard break (trailing "\") — otherwise GitHub
    collapses the soft breaks and renders all medals on one visual line.
    """
    if not candidates:
        lines.append("_No free models with confirmed support right now._")
        return

    def _link(m: Model) -> str:
        name = esc(model_short(m))
        return f"[{name}]({esc(m.model_url)})" if m.model_url else name

    podium = candidates[:3]
    for i, (medal, m) in enumerate(zip(("🥇", "🥈", "🥉"), podium)):
        provider = providers_by_id.get(m.provider_id)
        line = (
            f"{medal} **{_link(m)}** · {ctx_short(m.context_length)} ctx · "
            f"{caps_with_capabilities(m)} · "
            f"{provider.name if provider else m.provider_id}"
        )
        if i < len(podium) - 1:
            line += "\\"  # GFM hard break: medal stays on its own line
        lines.append(line)
    rest = candidates[3:]
    if rest:
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary><b>More {details_label} free models ({len(rest)})</b></summary>")
        lines.append("")
        for m in rest:
            lines.append(f"- {_link(m)} — {ctx_short(m.context_length)}")
        lines.append("")
        lines.append("</details>")
    # Podium lines run modality + capability icons together; close the
    # section with one shared combined legend (empty candidates return
    # above, so the legend only appears when a podium was rendered).
    lines.append("")
    lines.append(legend_line(capabilities=True))


def _api_compat_label(compatibility: list[str]) -> str:
    if compatibility == ["openai"]:
        return "OpenAI-compatible"
    return "/".join(compatibility)


def _api_compat_footnote(
    models: list[Model], providers_by_id: dict[str, Provider]
) -> str:
    """Footnote replacing the old Rate Limit / API columns (first mention order)."""
    seen: set[str] = set()
    parts: list[str] = []
    for m in models:
        if m.provider_id in seen:
            continue
        seen.add(m.provider_id)
        provider = providers_by_id.get(m.provider_id)
        if provider and provider.api_compatibility:
            label = _api_compat_label(provider.api_compatibility)
            parts.append(f"{provider.name} — {label}")
    if not parts:
        return "Rate limits are rarely published; see provider pages."
    return (
        "Rate limits are rarely published; see provider pages. "
        "API compatibility: " + "; ".join(parts) + "."
    )


def generate_readme(
    providers: list[Provider],
    offers: list[Offer],
    models: list[Model],
    scores: dict[str, ProviderScore],
    changes: list[Change],
    generated_on: date,
) -> str:
    providers_by_id = {p.id: p for p in providers}
    models_by_provider: dict[str, list[Model]] = {}
    for m in models:
        models_by_provider.setdefault(m.provider_id, []).append(m)
    for lst in models_by_provider.values():
        lst.sort(key=lambda m: (-(m.context_length or 0), m.model_id))
    free_by_provider = {
        pid: [m for m in lst if m.free]
        for pid, lst in models_by_provider.items()
    }

    lines: list[str] = []
    lines.append("# ⛏️ TokenMiner")
    lines.append("")
    lines.append(f"> {SUBTITLE}")
    lines.append("")
    lines.append(
        f"Auto-updated **{generated_on.isoformat()}** · "
        f"{len(providers)} providers · {len(offers)} offers · "
        f"{sum(len(v) for v in free_by_provider.values())} free models tracked"
    )
    lines.append("")

    # §19 Best deals -----------------------------------------------------
    lines.append("# 🔥 Best Free AI Deals Right Now")
    lines.append("")
    best = [
        o for o in offers
        if o.status == "active" and o.confidence in ("official", "high")
    ]
    best.sort(key=lambda o: -scores.get(o.provider_id, ProviderScore(o.provider_id, 0, "D", {})).score)
    if best:
        lines.append("| # | Provider | Deal | Best Model | Ctx | Score | Get |")
        lines.append("|---|---|---|---|---|---|---|")
        for rank, offer in enumerate(best, 1):
            provider = providers_by_id.get(offer.provider_id)
            score = scores.get(offer.provider_id)
            free_count = len(free_by_provider.get(offer.provider_id, []))
            best_model = _best_free_model(free_by_provider.get(offer.provider_id, []))
            get_url = offer.claim_url or (provider.signup_url if provider else "") or ""
            get_cell = f"[→]({esc(get_url)})" if get_url else "—"
            if best_model:
                name = esc(model_short(best_model))
                model_cell = (
                    f"[{name}]({esc(best_model.model_url)})"
                    if best_model.model_url else name
                )
                ctx_cell = ctx_short(best_model.context_length)
            else:
                model_cell = "—"
                ctx_cell = "—"
            score_cell = f"{score.score} {score.grade}" if score else "—"
            lines.append(
                f"| {rank} "
                f"| {provider_cell(provider, offer.provider_id)} "
                f"| {esc(deal_short(offer, free_count))} "
                f"| {model_cell} "
                f"| {ctx_cell} "
                f"| {esc(score_cell)} "
                f"| {get_cell} |"
            )
    else:
        lines.append("_No officially verified active offers right now._")
    lines.append("")

    # §20 Free models ----------------------------------------------------
    lines.append("# 🆓 Free Models")
    lines.append("")
    all_free = sorted(
        (m for lst in free_by_provider.values() for m in lst),
        key=lambda m: (-(m.context_length or 0), m.provider_id, m.model_id),
    )
    if all_free:
        lines.append("| Provider | Model | Ctx | Caps | Link |")
        lines.append("|---|---|---|---|---|")
        for m in all_free:
            provider = providers_by_id.get(m.provider_id)
            lines.append(
                f"| {provider_cell(provider, m.provider_id)} "
                f"| {esc(model_short(m))} "
                f"| {ctx_short(m.context_length)} "
                f"| {caps_icons(m)} "
                f"| [↗]({esc(m.model_url)}) |"
            )
        lines.append("")
        lines.append(_api_compat_footnote(all_free, providers_by_id))
        lines.append("")
        lines.append(legend_line())
    else:
        lines.append("_No free models detected._")
    lines.append("")

    # §21 Free credits ---------------------------------------------------
    lines.append("# 🎁 Free Credits")
    lines.append("")
    credits = [
        o for o in offers
        if o.type in ("signup_credit", "recurring_credit", "student", "promotion")
        and o.status in ("active", "uncertain")
    ]
    credits.sort(key=lambda o: (o.provider_id, o.id))
    if credits:
        lines.append("| Provider | Amount | Requirement | Verified | Claim |")
        lines.append("|---|---|---|---|---|")
        for o in credits:
            provider = providers_by_id.get(o.provider_id)
            verified = to_iso(o.last_verified) or ("⚠️ unverified" if o.status == "uncertain" else "—")
            claim_cell = f"[Claim]({esc(o.claim_url)})" if o.claim_url else "—"
            lines.append(
                f"| {provider_cell(provider, o.provider_id)} "
                f"| {esc(credit_amount(o))} "
                f"| {esc(requirement_short(o))} "
                f"| {esc(verified)} "
                f"| {claim_cell} |"
            )
    else:
        lines.append("_No free credits found right now._")
    lines.append("")

    # §22 Coding / Reasoning ---------------------------------------------
    for heading, flag, blurb, details_label in (
        ("💻 Best Free Models for Coding", "supports_tools",
         "Free models that support tool calling — the practical proxy for coding agents.",
         "tool-calling"),
        ("🧠 Best Free Models for Reasoning", "supports_reasoning",
         "Free models exposing a reasoning parameter — the practical proxy for reasoning.",
         "reasoning"),
    ):
        lines.append(f"# {heading}")
        lines.append("")
        lines.append(f"> ℹ️ {blurb} **Not a formal benchmark.**")
        lines.append("")
        candidates = sorted(
            (m for m in all_free if getattr(m, flag)),
            key=lambda m: (-(m.context_length or 0), m.provider_id, m.model_id),
        )
        _podium_and_details(lines, candidates, providers_by_id, details_label)
        lines.append("")

    # §23 Recently changed ------------------------------------------------
    lines.append("# 🕒 Recently Changed")
    lines.append("")
    if changes:
        for change in changes[:10]:
            lines.append(f"- {change.symbol} {change.text}")
        lines.append("")
        lines.append("Full history in [CHANGELOG.md](CHANGELOG.md).")
    else:
        lines.append("_No changes since last run._")
    lines.append("")

    # Footer ----------------------------------------------------------------
    lines.append("# 📖 Data & Verification")
    lines.append("")
    lines.append(
        "All data is auto-collected by `python -m tokenminer` from public, "
        "official pages (no secrets, no logins). Every offer links its "
        "`source_url`; every number was read from that source when it was "
        "recorded — anything unverifiable stays `null`/uncertain rather than "
        "guessed. Scores are computed by fixed rules in "
        "[`tokenminer/scoring/scorer.py`](tokenminer/scoring/scorer.py), not a "
        "formal benchmark. Deals change constantly: always confirm on the "
        "provider's page before relying on one."
    )
    lines.append("")
    lines.append(
        "[SPEC](SPEC.md) · [CHANGELOG](CHANGELOG.md) · "
        "[Provider pages](docs/providers/) · "
        "[LICENSE](LICENSE) · [CONTRIBUTING](CONTRIBUTING.md)"
    )
    lines.append("")
    return "\n".join(lines)
