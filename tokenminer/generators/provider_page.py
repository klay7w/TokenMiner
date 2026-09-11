"""docs/providers/<id>.md generator (SPEC §24).

Fixed sections: Overview / Current Free Offers / Free Models / API /
Context Windows / Rate Limits / Requirements / Pros / Cons / TokenMiner Score /
Recommended For / Links / Sources / Last Verified. Pros/Cons are derived from
data, never invented.
"""

from __future__ import annotations

from ..models import Model, Offer, Provider
from ..scoring.scorer import ProviderScore
from ..utils.time import to_iso
from .format import (
    caps_with_capabilities,
    ctx_short,
    esc,
    favicon_img,
    legend_line,
    model_short,
)


def generate_provider_page(
    provider: Provider,
    offers: list[Offer],
    models: list[Model],
    score: ProviderScore | None,
) -> str:
    provider_offers = [o for o in offers if o.provider_id == provider.id]
    provider_models = [m for m in models if m.provider_id == provider.id]
    free_models = sorted(
        (m for m in provider_models if m.free),
        key=lambda m: (-(m.context_length or 0), m.model_id),
    )
    lines: list[str] = []
    add = lines.append

    logo = favicon_img(provider, 20)
    add(f"# {logo + ' ' if logo else ''}{provider.name}")
    add("")
    add(f"> Category: **{provider.category}** · Status: **{provider.status}**")
    add("")

    add("## Overview")
    add("")
    add(provider.description or "_No description._")
    add("")

    add("## Current Free Offers")
    add("")
    if provider_offers:
        for o in provider_offers:
            value = f"${o.value:g}{'/mo' if o.recurring else ''}" if o.value is not None else "—"
            add(
                f"- **{o.title}** — type `{o.type}`, value {value}, "
                f"status `{o.status}`, confidence `{o.confidence}`"
                + (" ⚠️ **Stale**" if o.stale else "")
            )
            if o.description:
                add(f"  - {o.description}")
            if o.claim_url:
                add(f"  - Claim: {o.claim_url}")
            if o.source_url:
                add(f"  - Source: {o.source_url}")
    else:
        add("_No offers recorded for this provider._")
    add("")

    add("## Free Models")
    add("")
    if free_models:
        add("| Model | Ctx | Caps | Link |")
        add("|---|---|---|---|")
        for m in free_models:
            add(
                f"| {esc(model_short(m))} | {ctx_short(m.context_length)} "
                f"| {caps_with_capabilities(m)} | [↗]({m.model_url}) |"
            )
        add("")
        add(legend_line(capabilities=True))
    else:
        add("_No free models tracked for this provider (yet)._")
    add("")

    add("## API")
    add("")
    if provider.api_base_url:
        add(f"- API base: `{provider.api_base_url}`")
    if provider.api_compatibility:
        add(f"- Compatibility: {', '.join(f'`{c}`' for c in provider.api_compatibility)}")
    if not provider.api_base_url and not provider.api_compatibility:
        add("_No API details recorded._")
    add("")

    add("## Context Windows")
    add("")
    contexts = [m.context_length for m in free_models if m.context_length]
    if contexts:
        add(f"- Largest free-model context: **{ctx_short(max(contexts))}**")
        add(f"- Free models with published context: {len(contexts)} of {len(free_models)}")
    else:
        add("_No official context numbers available (recorded as null, never guessed)._")
    add("")

    add("## Rate Limits")
    add("")
    limits = [m.rate_limit for m in free_models if m.rate_limit]
    if limits:
        for m in free_models:
            if m.rate_limit:
                add(f"- `{m.model_id}`: {m.rate_limit}")
    else:
        add("_No officially published rate-limit numbers recorded for free usage._")
    add("")

    add("## Requirements")
    add("")
    add(f"- Account required: {'yes' if provider.requires_account else 'no'}")
    reqs = []
    for o in provider_offers:
        if o.requires_payment_method:
            reqs.append("💳 payment method for at least one offer")
        if o.requires_phone:
            reqs.append("📱 phone verification for at least one offer")
        if o.requires_student_verification:
            reqs.append("🎓 student verification for at least one offer")
        if o.region_limit:
            reqs.append(f"🌍 region restricted: {o.region_limit}")
    for r in sorted(set(reqs)):
        add(f"- {r}")
    add("")

    add("## Pros")
    add("")
    pros: list[str] = []
    if free_models:
        pros.append(f"{len(free_models)} free model(s) available")
    if any((m.context_length or 0) >= 200_000 for m in free_models):
        pros.append("long-context free models (≥200K)")
    if any(m.supports_tools for m in free_models if m.supports_tools):
        pros.append("free models with tool calling")
    if any(m.supports_reasoning for m in free_models if m.supports_reasoning):
        pros.append("free models with reasoning support")
    if any(m.supports_vision for m in free_models if m.supports_vision):
        pros.append("multimodal free models")
    if any(o.recurring for o in provider_offers if o.recurring):
        pros.append("recurring free credits")
    if len(provider.api_compatibility) >= 2:
        pros.append(f"multi-format API ({', '.join(provider.api_compatibility)})")
    if score and score.grade in ("S", "A"):
        pros.append(f"high TokenMiner score ({score.score}/100, grade {score.grade})")
    for p in pros:
        add(f"- {p}")
    if not pros:
        add("_Nothing notable derived from current data._")
    add("")

    add("## Cons")
    add("")
    cons: list[str] = []
    if not free_models and not any(o.status == "active" for o in provider_offers):
        cons.append("no free offering verified right now")
    if any(o.requires_payment_method for o in provider_offers if o.requires_payment_method):
        cons.append("payment method required for some offers")
    if any(o.requires_phone for o in provider_offers if o.requires_phone):
        cons.append("phone verification required for some offers")
    if any(o.requires_student_verification for o in provider_offers if o.requires_student_verification):
        cons.append("student verification required for some offers")
    if any(o.stale for o in provider_offers if o.stale):
        cons.append("some offers not re-verified within 7 days")
    if provider.category == "candidate":
        cons.append("candidate provider — not yet fully integrated")
    unknown_ctx = [m for m in free_models if m.context_length is None]
    if unknown_ctx and free_models and len(unknown_ctx) == len(free_models):
        cons.append("free-model context windows not officially published")
    for c in cons:
        add(f"- {c}")
    if not cons:
        add("_No notable drawbacks derived from current data._")
    add("")

    add("## TokenMiner Score")
    add("")
    if score:
        add(f"**{score.score}/100 — grade {score.grade}**")
        add("")
        add("| Component | Points | Max |")
        add("|---|---|---|")
        from ..scoring.scorer import WEIGHTS
        for name, pts in score.components.items():
            add(f"| {name} | {pts:g} | {WEIGHTS[name]} |")
        if score.risk_tags:
            add("")
            add(f"Risk tags: {' · '.join(score.risk_tags)}")
    else:
        add("_Not scored (no data)._")
    add("")

    add("## Recommended For")
    add("")
    if score and score.best_for:
        for label in score.best_for:
            add(f"- {label}")
    else:
        add("_Insufficient evidence to recommend._")
    add("")

    add("## Links")
    add("")
    for label, url in (
        ("Official", provider.official_url), ("Pricing", provider.pricing_url),
        ("Docs", provider.docs_url), ("Models", provider.models_url),
        ("Signup", provider.signup_url),
    ):
        if url:
            add(f"- [{label}]({url})")
    add("")

    add("## Sources")
    add("")
    if provider.sources:
        for s in provider.sources:
            add(f"- {s}")
    else:
        add("_No sources recorded._")
    add("")

    add("## Last Verified")
    add("")
    add(f"- Provider: {to_iso(provider.last_verified) or 'never'}")
    for o in provider_offers:
        add(f"- Offer `{o.id}`: {to_iso(o.last_verified) or 'never'}"
            + (" ⚠️ stale" if o.stale else ""))
    add("")
    return "\n".join(lines)
