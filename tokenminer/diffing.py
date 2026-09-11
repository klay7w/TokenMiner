"""Change detection (SPEC §27).

Pure functions comparing previous vs new offers / models / providers,
producing display-ready change entries ``{date, symbol, text}``.
Symbols: ``+`` new, ``-`` removed, ``⚠`` changed.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Model, Offer, Provider
from .utils.time import today


@dataclass
class Change:
    date: str
    symbol: str  # "+" | "-" | "⚠"
    text: str

    def render(self) -> str:
        return f"{self.date} {self.symbol} {self.text}"


def diff_data(
    old_providers: list[Provider],
    new_providers: list[Provider],
    old_offers: list[Offer],
    new_offers: list[Offer],
    old_models: list[Model],
    new_models: list[Model],
) -> list[Change]:
    changes: list[Change] = []
    date = today().isoformat()
    changes += _diff_providers(old_providers, new_providers, date)
    changes += _diff_offers(old_offers, new_offers, date)
    changes += _diff_models(old_models, new_models, date)
    return changes


def _diff_providers(old: list[Provider], new: list[Provider], date: str) -> list[Change]:
    changes: list[Change] = []
    old_by_id = {p.id: p for p in old}
    new_by_id = {p.id: p for p in new}
    for pid, p in new_by_id.items():
        if pid not in old_by_id:
            changes.append(Change(date, "+", f"New provider: {p.name} ({pid})"))
    for pid, p in old_by_id.items():
        if pid not in new_by_id:
            changes.append(Change(date, "-", f"Provider removed: {p.name} ({pid})"))
        elif p.status != new_by_id[pid].status:
            changes.append(Change(
                date, "⚠",
                f"{p.name}: status changed {p.status} → {new_by_id[pid].status}",
            ))
    return changes


def _diff_offers(old: list[Offer], new: list[Offer], date: str) -> list[Change]:
    changes: list[Change] = []
    old_by_id = {o.id: o for o in old}
    new_by_id = {o.id: o for o in new}
    for oid, o in new_by_id.items():
        prev = old_by_id.get(oid)
        if prev is None:
            changes.append(Change(date, "+", f"New offer: {o.title} ({o.provider_id})"))
            continue
        if prev.status == "active" and o.status == "expired":
            changes.append(Change(date, "-", f"Offer expired: {o.title} ({o.provider_id})"))
        elif prev.status != o.status:
            changes.append(Change(
                date, "⚠",
                f"{o.title}: status changed {prev.status} → {o.status}",
            ))
        if prev.value != o.value and (prev.value is not None or o.value is not None):
            changes.append(Change(
                date, "⚠",
                f"{o.title}: credits changed {prev.value:g} → {o.value:g}",
            ))
        if prev.end_date != o.end_date:
            changes.append(Change(
                date, "⚠",
                f"{o.title}: expiration changed {prev.end_date} → {o.end_date}",
            ))
    for oid, o in old_by_id.items():
        if oid not in new_by_id:
            changes.append(Change(date, "-", f"Offer removed: {o.title} ({o.provider_id})"))
    return changes


def _diff_models(old: list[Model], new: list[Model], date: str) -> list[Change]:
    """Only free models are tracked in diffs (SPEC §27)."""
    changes: list[Change] = []
    key = lambda m: (m.provider_id, m.model_id)  # noqa: E731
    old_free = {key(m): m for m in old if m.free}
    new_free = {key(m): m for m in new if m.free}
    for k, m in new_free.items():
        prev = old_free.get(k)
        if prev is None:
            changes.append(Change(
                date, "+", f"New free model: {m.model_id} ({m.provider_id})",
            ))
        else:
            if prev.context_length != m.context_length:
                changes.append(Change(
                    date, "⚠",
                    f"{m.model_id} ({m.provider_id}): context changed "
                    f"{prev.context_length} → {m.context_length}",
                ))
            if prev.rate_limit != m.rate_limit:
                changes.append(Change(
                    date, "⚠",
                    f"{m.model_id} ({m.provider_id}): rate limit changed",
                ))
            if prev.input_price != m.input_price or prev.output_price != m.output_price:
                changes.append(Change(
                    date, "⚠", f"{m.model_id} ({m.provider_id}): pricing changed",
                ))
    for k, m in old_free.items():
        if k not in new_free:
            changes.append(Change(
                date, "-", f"Free model removed: {m.model_id} ({m.provider_id})",
            ))
    return changes
