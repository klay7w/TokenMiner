"""Load/save the data files (SPEC §5, §28).

- data/providers.yaml : seed registry (list of providers), enriched in place
- data/offers.json    : sorted by (provider_id, id)
- data/models.json    : sorted by (provider_id, model_id) — ALL models
- data/history/YYYY-MM-DD.json : snapshot (providers+offers+free models),
  written only when data substantively changed
- data/update_summary.txt     : machine-readable run summary for CI PR body
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from .models import Model, Offer, Provider

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROVIDERS_PATH = DATA / "providers.yaml"
OFFERS_PATH = DATA / "offers.json"
MODELS_PATH = DATA / "models.json"
SEED_OFFERS_PATH = DATA / "seeds" / "offers.yaml"
HISTORY_DIR = DATA / "history"
GENERIC_STATE_PATH = DATA / "generic_state.json"
SUMMARY_PATH = DATA / "update_summary.txt"


# ---------------------------------------------------------------- providers
def load_providers(path: Path = PROVIDERS_PATH) -> list[Provider]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Provider(**entry) for entry in (raw or [])]


def save_providers(providers: list[Provider], path: Path = PROVIDERS_PATH) -> None:
    payload = [json.loads(p.model_dump_json()) for p in providers]
    payload.sort(key=lambda p: p["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


# ------------------------------------------------------------------- offers
def load_offers(path: Path = OFFERS_PATH) -> list[Offer]:
    return _load_models_file(path, Offer)


def save_offers(offers: list[Offer], path: Path = OFFERS_PATH) -> None:
    payload = [json.loads(o.model_dump_json()) for o in offers]
    payload.sort(key=lambda o: (o["provider_id"], o["id"]))
    _write_json(path, payload)


# ------------------------------------------------------------------- models
def load_models(path: Path = MODELS_PATH) -> list[Model]:
    return _load_models_file(path, Model)


def save_models(models: list[Model], path: Path = MODELS_PATH) -> None:
    payload = [json.loads(m.model_dump_json()) for m in models]
    payload.sort(key=lambda m: (m["provider_id"], m["model_id"]))
    _write_json(path, payload)


# ------------------------------------------------------------------ history
def save_history_snapshot(
    providers: list[Provider], offers: list[Offer], models: list[Model],
    day: date, directory: Path = HISTORY_DIR,
) -> Path:
    free_models = [m for m in models if m.free]
    payload = {
        "date": day.isoformat(),
        "providers": [json.loads(p.model_dump_json()) for p in providers],
        "offers": [json.loads(o.model_dump_json()) for o in offers],
        "free_models": [json.loads(m.model_dump_json()) for m in free_models],
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{day.isoformat()}.json"
    _write_json(path, payload)
    return path


def list_history_snapshots(directory: Path = HISTORY_DIR) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.glob("????-??-??.json") if p.is_file()
    )


def load_snapshot(path: Path) -> tuple[list[Provider], list[Offer], list[Model]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    providers = [Provider(**p) for p in raw.get("providers", [])]
    offers = [Offer(**o) for o in raw.get("offers", [])]
    models = [Model(**m) for m in raw.get("free_models", [])]
    return providers, offers, models


# ----------------------------------------------------------------- helpers
def _load_models_file(path: Path, cls):
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [cls(**entry) for entry in (raw or [])]


def _write_json(path: Path, payload: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
