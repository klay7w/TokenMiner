"""Shared table-formatting helpers for README / provider pages (SPEC §18–24).

Goal: keep every generated table inside GitHub's ~1012px content area —
compact cells (K/M context, icon caps, short deal labels) plus provider
favicons derived from ``Provider.official_url``. Pure functions, no I/O.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..models import Model, Offer, Provider
from ..utils.time import to_iso

# Modality icons in fixed display order (README legend must match).
MODALITY_ICONS: tuple[tuple[str, str], ...] = (
    ("text", "📝"),
    ("image", "🖼️"),
    ("video", "🎬"),
    ("audio", "🔊"),
    ("embedding", "🧩"),
)
CAPABILITY_ICONS: tuple[tuple[str, str], ...] = (
    ("tools", "🛠️"),
    ("vision", "👁️"),
    ("reasoning", "🧠"),
)

_FAVICON = "https://www.google.com/s2/favicons?domain={domain}&sz=32"

# Shared rank legend (SPEC §40): one line under every rank-iconized table.
RANK_LEGEND = (
    "Rank: 🏆 [LMArena](https://llmarena.ai) text-leaderboard rank"
    " · 🔥 [OpenRouter](https://openrouter.ai) weekly usage rank"
    " · — unranked"
)


def free_model_sort_key(m: Model) -> tuple:
    """Tiered free-model ordering (SPEC §40): LMArena rank (1 = best),
    then OpenRouter weekly usage rank, then context length desc, id asc."""
    return (
        m.arena_rank is None,
        m.arena_rank if m.arena_rank is not None else 0,
        m.usage_rank is None,
        m.usage_rank if m.usage_rank is not None else 0,
        -(m.context_length or 0),
        m.model_id,
    )


def free_rank_cell(m: Model) -> str:
    """Compact Rank cell: arena rank, else weekly usage rank, else —."""
    if m.arena_rank is not None:
        return f"#{m.arena_rank} 🏆"
    if m.usage_rank is not None:
        return f"#{m.usage_rank} 🔥"
    return "—"


def esc(text: object) -> str:
    """Escape a value for use inside a markdown table cell."""
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def ctx_short(n: int | None) -> str:
    """Compact context size: 1_000_000 -> "1M", 262_144 -> "262K", None -> "—"."""
    if not n:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.0f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def favicon_domain(provider: Provider) -> str | None:
    """Hostname for the favicon, derived from official_url (www. stripped)."""
    if not provider.official_url:
        return None
    host = urlsplit(provider.official_url).netloc.split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def favicon_img(provider: Provider | None, width: int = 16) -> str:
    """External favicon <img> tag, or "" when no official_url is recorded."""
    if provider is None:
        return ""
    domain = favicon_domain(provider)
    if not domain:
        return ""
    return f'<img src="{_FAVICON.format(domain=domain)}" width="{width}" valign="middle">'


def provider_cell(provider: Provider | None, fallback_id: str = "") -> str:
    """Compact Provider cell: favicon + name linked to its provider page.

    Without a recorded official_url the cell degrades to the (linked) name.
    """
    name = provider.name if provider else (fallback_id or "—")
    link = f"docs/providers/{provider.id}.md" if provider else ""
    img = favicon_img(provider, 16)
    text = esc(name)
    if link:
        return f"{img} [{text}]({link})".strip()
    return text


def model_short(m: Model) -> str:
    """Compact human display name for a model.

    Strips a trailing " (free)" and a leading "Developer: " prefix (only when
    the part before ":" equals the developer, case-insensitive). When the
    recorded name just mirrors the raw id (TokenRouter), the "developer/"
    prefix is dropped instead. Never empty.
    """
    name = (m.name or "").strip()
    if not name:
        return m.model_id
    if name == m.model_id:
        # display name mirrors the raw id (TokenRouter): drop the developer/ prefix
        short = m.model_id.split("/", 1)[1] if "/" in m.model_id else m.model_id
        return short.strip() or m.model_id
    if name.endswith(" (free)"):
        name = name[: -len(" (free)")].strip()
    prefix = re.match(r"^([^:]+):\s+(.*)$", name)
    if prefix and m.developer and prefix.group(1).strip().lower() == m.developer.strip().lower():
        name = prefix.group(2).strip()
    return name or m.model_id


def caps_icons(m: Model) -> str:
    """Modality emoji for a model, in fixed order, concatenated (no spaces)."""
    types = set(m.model_type or ())
    return "".join(icon for name, icon in MODALITY_ICONS if name in types)


def caps_with_capabilities(m: Model) -> str:
    """Modality icons plus capability icons (provider pages): 🛠️ 👁️ 🧠."""
    caps = caps_icons(m)
    if m.supports_tools:
        caps += "🛠️"
    if m.supports_vision:
        caps += "👁️"
    if m.supports_reasoning:
        caps += "🧠"
    return caps


def _currency_parts(offer: Offer) -> tuple[str, str]:
    usd = (offer.currency or "USD") == "USD"
    return ("$" if usd else "", "" if usd else " USD")


def _deadline_suffix(offer: Offer) -> str:
    suffix = ""
    if offer.requires_payment_method:
        suffix += " 💳"
    if offer.end_date:
        iso = to_iso(offer.end_date) or ""
        if len(iso) >= 10:
            suffix += f" ⏳{iso[5:10]}"
    return suffix


def deal_short(offer: Offer, free_model_count: int) -> str:
    """One compact label for the Best Deals "Deal" column."""
    sym, cur = _currency_parts(offer)

    def amount(value: float) -> str:
        return f"{sym}{value:g}{cur}"

    tail = _deadline_suffix(offer)
    if offer.type == "free_tier":
        if free_model_count:
            plural = "s" if free_model_count != 1 else ""
            return f"{free_model_count} free model{plural} ♾️" + tail
        return "Free tier ♾️" + tail
    if offer.type == "signup_credit":
        base = f"{amount(offer.value)} credit" if offer.value is not None else "Signup credit"
        if offer.new_users_only:
            base += " 🎁"
        return base + tail
    if offer.type == "trial":
        return "Trial ⏳" + tail
    if offer.type == "student":
        if offer.value is not None:
            base = amount(offer.value) + ("/mo" if offer.recurring else "")
        else:
            base = "Student discount"
        return base + " 🎓" + tail
    if offer.type == "recurring_credit" or offer.recurring:
        if offer.value is not None:
            return f"{amount(offer.value)}/mo ♻️" + tail
        return "Recurring credit ♻️" + tail
    # promotion / developer_program / free_model / unknown: short description
    text = (offer.description or offer.title or "").split(". ")[0].strip()
    return text[:40] + ("…" if len(text) > 40 else "") + tail


def credit_amount(offer: Offer) -> str:
    """Compact amount string for the Free Credits table ("$5 once", "$10/mo ♻️")."""
    sym, cur = _currency_parts(offer)
    if offer.value is not None:
        if offer.recurring:
            base = f"{sym}{offer.value:g}{cur}/mo ♻️"
        else:
            base = f"{sym}{offer.value:g}{cur} once"
    elif offer.type == "free_tier":
        base = "Free tier"
    else:
        text = (offer.description or offer.title or "").split(". ")[0].strip()
        base = text[:40] + ("…" if len(text) > 40 else "") or offer.type.replace("_", " ")
    if offer.end_date:
        iso = to_iso(offer.end_date) or ""
        if len(iso) >= 10:
            base = f"⏳ {iso[5:10]} {base}"
    return base


def requirement_short(offer: Offer) -> str:
    """Short requirement phrases for the Free Credits table."""
    parts: list[str] = []
    if offer.new_users_only:
        parts.append("New users")
    if offer.requires_student_verification:
        parts.append("🎓 Student")
    if offer.requires_payment_method:
        parts.append("💳 Card")
    if offer.requires_phone:
        parts.append("📱 Phone")
    if offer.region_limit:
        parts.append(f"🌍 {offer.region_limit}")
    return " · ".join(parts) or "Account"


def legend_line(capabilities: bool = False) -> str:
    """Legend line rendered under iconized tables.

    The combined variant (capabilities=True) spells out the difference
    between the two look-alike image icons: 🖼️ marks image I/O
    (generation models) while 👁️ means image input (vision).
    """
    if not capabilities:
        return "*" + " · ".join(f"{icon} {name}" for name, icon in MODALITY_ICONS) + "*"
    # 👁️ sits right beside 🖼️ and must not repeat in the capability tail.
    entries: list[str] = []
    for name, icon in MODALITY_ICONS:
        entries.append(f"{icon} image I/O" if name == "image" else f"{icon} {name}")
        if name == "image":
            entries.append("👁️ image input (vision)")
    entries.extend(f"{icon} {name}" for name, icon in CAPABILITY_ICONS if name != "vision")
    return "*" + " · ".join(entries) + "*"
