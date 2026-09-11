"""Update / validate / generate pipeline (SPEC §30–31).

`update`: seeds + existing data -> collectors (per-provider try/except) ->
OfferValidator -> diff -> persist -> history snapshot (only on change) ->
regenerate docs. Exit 0 unless schema validation fails, data corrupts, or a
generator raises (then 1).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .collectors import (
    Collector,
    CollectorResult,
    GenericCollector,
    OpenRouterCollector,
    TokenRouterCollector,
)
from .diffing import Change, diff_data
from .generators import generate_changelog, generate_provider_page, generate_readme
from .models import Model, Offer, Provider
from .scoring import ProviderScore, score_provider
from .store import (
    DATA,
    GENERIC_STATE_PATH,
    MODELS_PATH,
    OFFERS_PATH,
    PROVIDERS_PATH,
    SEED_OFFERS_PATH,
    SUMMARY_PATH,
    list_history_snapshots,
    load_models,
    load_offers,
    load_providers,
    load_snapshot,
    save_history_snapshot,
    save_models,
    save_offers,
    save_providers,
)
from .utils.http import HttpClient
from .utils.time import today
from .validators import OfferValidator

ROOT = DATA.parent
DOCS_PROVIDERS = ROOT / "docs" / "providers"
README_PATH = ROOT / "README.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"

RUNTIME_FIELDS = ("first_seen", "last_checked", "last_verified", "stale", "status")


def log(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- seeds
def load_seed_offers(path: Path = SEED_OFFERS_PATH) -> list[Offer]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Offer(**entry) for entry in (raw or [])]


def _merge_offer_content(content: Offer, existing: Offer | None) -> Offer:
    """Content fields from source (seed/collector); runtime state preserved."""
    if existing is None:
        data = content.model_dump()
        if data.get("first_seen") is None:
            data["first_seen"] = today()
        return Offer(**data)
    data = content.model_dump()
    for field in RUNTIME_FIELDS:
        data[field] = getattr(existing, field)
    return Offer(**data)


# ---------------------------------------------------------------- update
def run_update() -> int:
    log(f"TokenMiner update — {today().isoformat()}")
    try:
        providers = load_providers()
        previous_providers = [p.model_copy(deep=True) for p in providers]
        previous_offers = load_offers()
        previous_models = load_models()
        seed_offers = load_seed_offers()
    except Exception as exc:  # schema/corruption -> exit 1 (SPEC §31)
        warn(f"data load failed: {exc}")
        return 1

    offers_by_id: dict[str, Offer] = {o.id: o for o in previous_offers}
    # seed offers: authoritative content, runtime state preserved
    for seed in seed_offers:
        offers_by_id[seed.id] = _merge_offer_content(seed, offers_by_id.get(seed.id))

    models_by_provider: dict[str, list[Model]] = {}
    for m in previous_models:
        models_by_provider.setdefault(m.provider_id, []).append(m)

    providers_by_id = {p.id: p for p in providers}
    generic_notes: list[str] = []

    with HttpClient() as http:
        # dedicated collectors
        dedicated: dict[str, Collector] = {
            "openrouter": OpenRouterCollector(),
            "tokenrouter": TokenRouterCollector(),
        }
        for pid, collector in dedicated.items():
            provider = providers_by_id.get(pid)
            if provider is None:
                warn(f"collector {pid}: no such provider in registry")
                continue
            try:
                result = collector.collect(http, provider)
            except Exception as exc:  # single provider failure must not stop run
                warn(f"collector {pid} failed: {exc}")
                continue
            _apply_result(pid, result, providers_by_id, offers_by_id,
                          models_by_provider)

        # generic collectors (tier 2/3 change detection)
        generic = GenericCollector(GENERIC_STATE_PATH)
        for provider in providers:
            if provider.collector != "generic":
                continue
            try:
                result = generic.collect(http, provider)
            except Exception as exc:
                warn(f"generic collector {provider.id} failed: {exc}")
                continue
            _apply_result(provider.id, result, providers_by_id, offers_by_id,
                          models_by_provider)
            for note in result.notes:
                generic_notes.append(note)

        # offer re-verification
        all_offers = list(offers_by_id.values())
        try:
            validator = OfferValidator()
            all_offers, vwarnings = validator.validate_offers(all_offers, http)
        except Exception as exc:
            warn(f"offer validator failed: {exc}")
            return 1
        for w in vwarnings:
            warn(w)

    offers = sorted(all_offers, key=lambda o: (o.provider_id, o.id))
    models = sorted(
        (m for lst in models_by_provider.values() for m in lst),
        key=lambda m: (m.provider_id, m.model_id),
    )

    changes = diff_data(
        previous_providers, providers, previous_offers, offers,
        previous_models, models,
    )
    for note in generic_notes:
        changes.append(Change(today().isoformat(), "⚠", note))

    # persist ---------------------------------------------------------
    try:
        save_providers(providers)
        save_offers(offers)
        save_models(models)
        if changes:
            save_history_snapshot(providers, offers, models, today())
            log(f"history snapshot saved ({len(changes)} changes)")
    except Exception as exc:
        warn(f"persist failed: {exc}")
        return 1

    # generate docs ----------------------------------------------------
    display_changes = changes if changes else _recent_changes()
    try:
        _generate_docs(providers, offers, models, display_changes)
    except Exception as exc:
        warn(f"doc generation failed: {exc}")
        return 1

    _write_summary(providers, offers, models, changes)
    log(f"done: {len(providers)} providers, {len(offers)} offers, "
        f"{sum(1 for m in models if m.free)} free models, "
        f"{len(changes)} changes")
    return 0


def _apply_result(
    pid: str,
    result: CollectorResult,
    providers_by_id: dict[str, Provider],
    offers_by_id: dict[str, Offer],
    models_by_provider: dict[str, list[Model]],
) -> None:
    if result.models:
        models_by_provider[pid] = result.models
    for offer in result.offers:
        offers_by_id[offer.id] = _merge_offer_content(
            offer, offers_by_id.get(offer.id)
        )
    provider = providers_by_id[pid]
    for key, value in result.provider_updates.items():
        if value is not None:
            setattr(provider, key, value)
    for note in result.notes:
        log(f"{pid}: {note}")
    for warning in result.warnings:
        warn(f"{pid}: {warning}")


# ---------------------------------------------------------------- generate
def _generate_docs(
    providers: list[Provider],
    offers: list[Offer],
    models: list[Model],
    changes: list[Change],
) -> None:
    scores: dict[str, ProviderScore] = {}
    for provider in providers:
        provider_offers = [o for o in offers if o.provider_id == provider.id]
        provider_models = [m for m in models if m.provider_id == provider.id]
        scores[provider.id] = score_provider(
            provider, provider_offers, provider_models
        )
    readme = generate_readme(providers, offers, models, scores, changes, today())
    README_PATH.write_text(readme, encoding="utf-8", newline="\n")

    DOCS_PROVIDERS.mkdir(parents=True, exist_ok=True)
    wanted = {f"{p.id}.md" for p in providers}
    for page in DOCS_PROVIDERS.glob("*.md"):
        if page.name not in wanted:
            page.unlink()
    for provider in providers:
        page = DOCS_PROVIDERS / f"{provider.id}.md"
        page.write_text(
            generate_provider_page(
                provider, offers, models, scores.get(provider.id)
            ),
            encoding="utf-8",
            newline="\n",
        )

    CHANGELOG_PATH.write_text(generate_changelog(), encoding="utf-8", newline="\n")


def _recent_changes() -> list[Change]:
    """Diff of the last two history snapshots (for generate/README).

    With a single snapshot (fresh repo), diff empty-vs-baseline so the
    README's Recently Changed section reflects the initial haul.
    """
    snaps = list_history_snapshots()
    if not snaps:
        return []
    if len(snaps) == 1:
        new = load_snapshot(snaps[-1])
        return diff_data([], new[0], [], new[1], [], new[2])
    old = load_snapshot(snaps[-2])
    new = load_snapshot(snaps[-1])
    return diff_data(old[0], new[0], old[1], new[1], old[2], new[2])


def run_generate() -> int:
    try:
        providers = load_providers()
        offers = load_offers()
        models = load_models()
        changes = _recent_changes()
        _generate_docs(providers, offers, models, changes)
    except Exception as exc:
        warn(f"generate failed: {exc}")
        return 1
    log(f"docs regenerated: {len(providers)} provider pages, README, CHANGELOG")
    return 0


# ---------------------------------------------------------------- validate
def run_validate() -> int:
    errors: list[str] = []
    try:
        providers = load_providers()
        log(f"providers.yaml: {len(providers)} OK")
    except Exception as exc:
        errors.append(f"providers.yaml: {exc}")
    try:
        offers = load_offers()
        log(f"offers.json: {len(offers)} OK")
    except Exception as exc:
        errors.append(f"offers.json: {exc}")
        offers = []
    try:
        models = load_models()
        log(f"models.json: {len(models)} OK")
    except Exception as exc:
        errors.append(f"models.json: {exc}")
        models = []
    try:
        seeds = load_seed_offers()
        log(f"seeds/offers.yaml: {len(seeds)} OK")
    except Exception as exc:
        errors.append(f"seeds/offers.yaml: {exc}")
        seeds = []

    provider_ids = {p.id for p in providers}
    for offer in offers + seeds:
        if offer.provider_id not in provider_ids:
            errors.append(
                f"offer {offer.id}: unknown provider_id {offer.provider_id}"
            )
    for model in models:
        if model.provider_id not in provider_ids:
            errors.append(
                f"model {model.model_id}: unknown provider_id {model.provider_id}"
            )

    if errors:
        for e in errors:
            warn(e)
        return 1
    log("all data files valid")
    return 0


# ---------------------------------------------------------------- summary
def _write_summary(
    providers: list[Provider],
    offers: list[Offer],
    models: list[Model],
    changes: list[Change],
) -> None:
    by_status: dict[str, int] = {}
    by_confidence: dict[str, int] = {}
    for o in offers:
        by_status[o.status] = by_status.get(o.status, 0) + 1
        by_confidence[o.confidence] = by_confidence.get(o.confidence, 0) + 1
    free = sum(1 for m in models if m.free)
    lines = [
        f"date: {today().isoformat()}",
        f"providers: {len(providers)}",
        f"offers: {len(offers)}",
        f"offers_by_status: {dict(sorted(by_status.items()))}",
        f"offers_by_confidence: {dict(sorted(by_confidence.items()))}",
        f"models: {len(models)}",
        f"free_models: {free}",
        f"changes: {len(changes)}",
    ]
    for change in changes[:20]:
        lines.append(f"change: {change.symbol} {change.text}")
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
