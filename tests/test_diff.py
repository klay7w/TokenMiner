"""Diff engine tests (SPEC §27)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from tokenminer.diffing import diff_data
from tokenminer.models import Model, Offer, Provider


def _provider(pid="p", status="active") -> Provider:
    return Provider(id=pid, name=pid.title(), status=status)


def _offer(oid, value=None, status="active", end_date=None) -> Offer:
    return Offer(id=oid, provider_id="p", title=f"T-{oid}", type="signup_credit",
                 value=value, status=status, end_date=end_date)


def _model(mid, free=True, ctx=None, rate=None) -> Model:
    return Model(provider_id="p", model_id=mid, free=free, context_length=ctx,
                 rate_limit=rate)


def _run(old_offers, new_offers, old_models=(), new_models=(),
         old_providers=(), new_providers=()):
    changes = diff_data(list(old_providers), list(new_providers),
                        list(old_offers), list(new_offers),
                        list(old_models), list(new_models))
    return [c.text for c in changes], changes


def test_publisher_documents_reconstructs_notes_from_history(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "publisher_policy.py"
    spec = importlib.util.spec_from_file_location("publisher_policy", path)
    publisher_policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher_policy)

    old, new = "data/history/2026-09-01.json", "data/history/2026-09-02.json"
    stamp = "2026-09-03"
    snapshot = {"providers": [_provider().model_dump()], "offers": [_offer("a").model_dump()]}
    blobs = {
        old: json.dumps(snapshot),
        new: json.dumps({**snapshot, "free_models": [_model("m1").model_dump()]}),
        "CHANGELOG.md": "changelog",
        "README.md": f"{stamp}: New free model: m1 (p)",
    }
    monkeypatch.setattr(publisher_policy, "git", lambda *args: f"{old}\n{new}\n".encode())
    monkeypatch.setattr(publisher_policy, "blob", lambda rev, path: blobs[path])
    monkeypatch.setattr(publisher_policy, "generate_changelog", lambda directory: "changelog")
    monkeypatch.setattr(publisher_policy, "generate_readme", lambda ps, os, ms, scores, notes, on:
                        "\n".join(note.render() for note in notes))
    publisher_policy.documents("base", "head", stamp, [], [], [], [], ["README.md"])


def test_new_offer():
    texts, _ = _run([], [_offer("a")])
    assert any("New offer: T-a" in t for t in texts)


def test_removed_offer():
    texts, _ = _run([_offer("a")], [])
    assert any("Offer removed: T-a" in t for t in texts)


def test_offer_expired():
    texts, changes = _run([_offer("a", status="active")],
                          [_offer("a", status="expired")])
    assert any("Offer expired" in t for t in texts)
    assert all(c.symbol == "-" for c in changes)


def test_credits_changed():
    texts, changes = _run([_offer("a", value=5)], [_offer("a", value=10)])
    assert any("credits changed 5 → 10" in t for t in texts)
    assert any(c.symbol == "⚠" for c in changes)


def test_expiration_changed():
    texts, _ = _run([_offer("a", end_date=None)],
                    [_offer("a", end_date="2026-12-31")])
    assert any("expiration changed" in t for t in texts)


def test_new_free_model():
    texts, _ = _run([], [], old_models=[], new_models=[_model("m1")])
    assert any("New free model: m1" in t for t in texts)


def test_free_model_removed():
    texts, _ = _run([], [], old_models=[_model("m1")], new_models=[])
    assert any("Free model removed: m1" in t for t in texts)


def test_free_model_becomes_paid_is_removal():
    texts, _ = _run([], [], old_models=[_model("m1")],
                    new_models=[_model("m1", free=False)])
    assert any("Free model removed: m1" in t for t in texts)


def test_context_changed():
    texts, _ = _run([], [], old_models=[_model("m1", ctx=1000)],
                    new_models=[_model("m1", ctx=2000)])
    assert any("context changed 1000 → 2000" in t for t in texts)


def test_rate_limit_changed():
    texts, _ = _run([], [], old_models=[_model("m1", rate=None)],
                    new_models=[_model("m1", rate="30 RPM")])
    assert any("rate limit changed" in t for t in texts)


def test_paid_model_changes_are_not_reported():
    texts, _ = _run([], [], old_models=[_model("x", free=False, ctx=1000)],
                    new_models=[_model("x", free=False, ctx=9000)])
    assert texts == []


def test_new_provider_and_status_change():
    texts, _ = _run([], [], old_providers=[], new_providers=[_provider()])
    assert any("New provider: P" in t for t in texts)
    texts, _ = _run([], [], old_providers=[_provider(status="active")],
                    new_providers=[_provider(status="unavailable")])
    assert any("status changed active → unavailable" in t for t in texts)


def test_no_changes_means_empty():
    texts, _ = _run([_offer("a", value=5)], [_offer("a", value=5)])
    assert texts == []


def test_change_render_format():
    _, changes = _run([], [_offer("a")])
    # Canonical format: ``YYYY-MM-DD: text`` — no bullet, no symbol.
    rendered = changes[0].render()
    assert rendered == f"{changes[0].date}: {changes[0].text}"
    assert rendered.startswith(changes[0].date)
    assert rendered[len(changes[0].date)] == ":"
    assert changes[0].symbol not in rendered
