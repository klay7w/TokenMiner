"""README.md generator (SPEC §18–23). Pure f-strings — no template engine."""

from __future__ import annotations

from datetime import date

from ..diffing import Change
from ..models import Model, Offer, Provider
from ..scoring.scorer import ProviderScore
from ..utils.time import to_iso

SUBTITLE = "Mine free AI models, API credits, tokens and developer deals."


def _esc(text: object) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _ctx(n: int | None) -> str:
    if not n:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.0f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _best_free_model(models: list[Model]) -> Model | None:
    if not models:
        return None
    return sorted(
        models,
        key=lambda m: (-(m.context_length or 0), bool(m.supports_tools), m.model_id),
    )[0]


def _quota_text(offer: Offer, free_count: int) -> str:
    if offer.value is not None:
        amount = f"${offer.value:g}" + ("/mo" if offer.recurring else "")
        return amount
    if offer.type == "free_tier" and free_count:
        return f"{free_count} free model{'s' if free_count != 1 else ''}"
    if offer.description:
        # first short sentence of the official description
        first = offer.description.split(". ")[0].strip()
        return first[:60] + ("…" if len(first) > 60 else "")
    return "—"


def _payment_text(offer: Offer) -> str:
    if offer.requires_payment_method is True:
        return "💳 Card"
    if offer.requires_phone is True:
        return "📱 Phone"
    if offer.requires_payment_method is False:
        return "No card"
    return "—"


def _requirement_text(offer: Offer) -> str:
    parts: list[str] = []
    if offer.new_users_only:
        parts.append("New users")
    if offer.requires_student_verification:
        parts.append("🎓 Student")
    if offer.requires_payment_method is True:
        parts.append("💳 Card")
    elif offer.requires_payment_method is False:
        parts.append("No card")
    if offer.requires_phone is True:
        parts.append("📱 Phone")
    if offer.region_limit:
        parts.append(f"🌍 {offer.region_limit}")
    return ", ".join(parts) or "Account"


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
        lines.append(
            "| Rank | Provider | Offer | Best Model | Context | Free Quota "
            "| Payment | Expire | Score | Get |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for rank, offer in enumerate(best, 1):
            provider = providers_by_id.get(offer.provider_id)
            score = scores.get(offer.provider_id)
            best_model = _best_free_model(free_by_provider.get(offer.provider_id, []))
            get_url = offer.claim_url or (provider.signup_url if provider else "") or ""
            score_cell = f"{score.score} ({score.grade})" if score else "—"
            lines.append(
                f"| {rank} "
                f"| {_esc(provider.name if provider else offer.provider_id)} "
                f"| {_esc(offer.title)} "
                f"| {_esc(best_model.name or best_model.model_id) if best_model else '—'} "
                f"| {_ctx(best_model.context_length) if best_model else '—'} "
                f"| {_esc(_quota_text(offer, len(free_by_provider.get(offer.provider_id, []))))} "
                f"| {_esc(_payment_text(offer))} "
                f"| {_esc(to_iso(offer.end_date) or 'No expiry')} "
                f"| **{_esc(score_cell)}** "
                f"| [Get]({_esc(get_url)}) |"
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
        lines.append("| Provider | Model | Type | Context | Rate Limit | API | Link |")
        lines.append("|---|---|---|---|---|---|---|")
        for m in all_free:
            provider = providers_by_id.get(m.provider_id)
            api = ",".join(provider.api_compatibility) if provider else ""
            lines.append(
                f"| {_esc(provider.name if provider else m.provider_id)} "
                f"| `{_esc(m.model_id)}` "
                f"| {_esc('+'.join(m.model_type))} "
                f"| {_ctx(m.context_length)} "
                f"| {_esc(m.rate_limit or '—')} "
                f"| {_esc(api or '—')} "
                f"| [↗]({_esc(m.model_url)}) |"
            )
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
        lines.append("| Provider | Credits | Type | Requirement | Expire | Verified | Claim |")
        lines.append("|---|---|---|---|---|---|---|")
        for o in credits:
            provider = providers_by_id.get(o.provider_id)
            credits_txt = (
                f"${o.value:g}{'/mo' if o.recurring else ''}" if o.value is not None else "—"
            )
            verified = to_iso(o.last_verified) or ("⚠️ unverified" if o.status == "uncertain" else "—")
            lines.append(
                f"| {_esc(provider.name if provider else o.provider_id)} "
                f"| {_esc(credits_txt)} "
                f"| {_esc(o.type)} "
                f"| {_esc(_requirement_text(o))} "
                f"| {_esc(to_iso(o.end_date) or 'No expiry')} "
                f"| {_esc(verified)} "
                f"| [Claim]({_esc(o.claim_url)}) |"
            )
    else:
        lines.append("_No free credits found right now._")
    lines.append("")

    # §22 Coding / Reasoning ---------------------------------------------
    for heading, flag, blurb in (
        ("💻 Best Free Models for Coding", "supports_tools",
         "Free models that support tool calling — the practical proxy for coding agents."),
        ("🧠 Best Free Models for Reasoning", "supports_reasoning",
         "Free models exposing a reasoning parameter — the practical proxy for reasoning."),
    ):
        lines.append(f"# {heading}")
        lines.append("")
        lines.append(f"> ℹ️ {blurb} **Not a formal benchmark.**")
        lines.append("")
        candidates = sorted(
            (m for m in all_free if getattr(m, flag)),
            key=lambda m: (-(m.context_length or 0), m.provider_id, m.model_id),
        )
        if candidates:
            medals = ("🥇", "🥈", "🥉")
            for i, m in enumerate(candidates[:3]):
                lines.append(
                    f"{medals[i]} `{m.model_id}` — {_ctx(m.context_length)} context, "
                    f"{m.provider_id} ([↗]({_esc(m.model_url)}))"
                )
            for m in candidates[3:10]:
                lines.append(f"- `{m.model_id}` — {_ctx(m.context_length)} context, {m.provider_id}")
        else:
            lines.append("_No free models with confirmed support right now._")
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
