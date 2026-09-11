"""Store tests: stable sorted dumps, history snapshot gating."""

from __future__ import annotations

import json
from datetime import date

from tokenminer import store
from tokenminer.models import Model, Offer, Provider


def test_offers_sorted_by_provider_then_id(tmp_path):
    path = tmp_path / "offers.json"
    offers = [
        Offer(id="b", provider_id="zeta", title="t", type="trial"),
        Offer(id="a", provider_id="zeta", title="t", type="trial"),
        Offer(id="z", provider_id="alpha", title="t", type="trial"),
    ]
    store.save_offers(offers, path)
    loaded = store.load_offers(path)
    assert [(o.provider_id, o.id) for o in loaded] == [
        ("alpha", "z"), ("zeta", "a"), ("zeta", "b"),
    ]
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert [(o["provider_id"], o["id"]) for o in raw] == [
        ("alpha", "z"), ("zeta", "a"), ("zeta", "b"),
    ]


def test_models_sorted_by_provider_then_model_id(tmp_path):
    path = tmp_path / "models.json"
    store.save_models([
        Model(provider_id="p", model_id="b/m"),
        Model(provider_id="p", model_id="a/m"),
        Model(provider_id="a", model_id="z/m"),
    ], path)
    loaded = store.load_models(path)
    assert [(m.provider_id, m.model_id) for m in loaded] == [
        ("a", "z/m"), ("p", "a/m"), ("p", "b/m"),
    ]


def test_providers_yaml_roundtrip(tmp_path):
    path = tmp_path / "providers.yaml"
    providers = [
        Provider(id="b", name="B", last_checked=date(2026, 9, 11)),
        Provider(id="a", name="A", watch_urls=["https://x.example"]),
    ]
    store.save_providers(providers, path)
    loaded = store.load_providers(path)
    assert [p.id for p in loaded] == ["a", "b"]
    assert loaded[0].watch_urls == ["https://x.example"]
    assert str(loaded[1].last_checked) == "2026-09-11"


def test_history_snapshot_contains_free_models_only(tmp_path):
    providers = [Provider(id="p", name="P")]
    offers = [Offer(id="o", provider_id="p", title="t", type="free_tier")]
    models = [
        Model(provider_id="p", model_id="free/m", free=True),
        Model(provider_id="p", model_id="paid/m", free=False),
    ]
    path = store.save_history_snapshot(providers, offers, models,
                                       date(2026, 9, 11), directory=tmp_path)
    assert path.name == "2026-09-11.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert [m["model_id"] for m in raw["free_models"]] == ["free/m"]
    assert len(raw["offers"]) == 1 and len(raw["providers"]) == 1
    p, o, m = store.load_snapshot(path)
    assert p[0].id == "p" and o[0].id == "o" and m[0].model_id == "free/m"
    assert store.list_history_snapshots(path.parent) == [path]


def test_load_missing_files_returns_empty(tmp_path):
    assert store.load_offers(tmp_path / "nope.json") == []
    assert store.load_models(tmp_path / "nope.json") == []
    assert store.load_providers(tmp_path / "nope.yaml") == []
    assert store.list_history_snapshots(tmp_path) == []
