"""LMArena collector tests (SPEC §40): RSC parsing, canonical name
matching with ambiguity rule, rank application, fail-soft artifact."""

from __future__ import annotations

import json

import pytest

from tokenminer.collectors import lmarena
from tokenminer.collectors.lmarena import (
    apply_arena_ranks,
    build_index,
    match_arena_name,
    parse_payload,
    refresh_arena,
)
from tokenminer.models import Model
from tokenminer.store import load_arena
from conftest import FakeHttpClient, load_fixture

ARENA_URL = lmarena.LEADERBOARD_URL


@pytest.fixture
def payload() -> str:
    return load_fixture("lmarena_flight.txt")


@pytest.fixture
def rows(payload) -> list[dict]:
    return parse_payload(payload)


class TestParsePayload:
    def test_extracts_entries_sorted_by_rank(self, rows):
        assert [r["rank"] for r in rows] == sorted(r["rank"] for r in rows)
        assert rows[0]["name"] == "claude-fable-5"
        assert rows[0]["rank"] == 1

    def test_keeps_best_rank_for_duplicate_names(self, payload):
        # inject two rows with the same display name, different ranks,
        # ahead of the fixture's real entries
        dup = (
            '{"rank":9,"rankUpper":8,"rankLower":10,'
            '"modelKey":"a","modelDisplayName":"dup-a"},'
            '{"rank":2,"rankUpper":1,"rankLower":3,'
            '"modelKey":"b","modelDisplayName":"dup-a"},'
        )
        text = payload.replace('"entries":[', f'"entries":[{dup}', 1)
        assert dup in text  # guard: injection must have landed
        by_name = {r["name"]: r for r in parse_payload(text)}
        assert by_name["dup-a"]["rank"] == 2  # best (lowest) rank wins

    def test_organization_best_effort_from_capability_rows(self, rows):
        by_name = {r["name"]: r for r in rows}
        # capability row carries org for "Inkling Small" (spaces normalized)
        assert by_name["Inkling Small"]["organization"] == "thinky"
        # capability rows without organization stay null (never guessed)
        assert by_name["gpt-4o"]["organization"] is None

    def test_unranked_capability_rows_are_not_entries(self, rows):
        names = {r["name"] for r in rows}
        assert "glm-5.2" not in names      # capability row only, no rank
        assert "kestrel-alpha" not in names  # capability row only

    def test_garbage_or_html_shell_yields_nothing(self):
        assert parse_payload("<!DOCTYPE html><html>") == []
        assert parse_payload("") == []


class TestMatchArenaName:
    def test_index_built(self, rows):
        index, ambiguous = build_index(rows)
        assert "inkling" in index
        assert "gpt-4o" in ambiguous  # gpt-4o + gpt-4o-latest collapse

    def test_free_suffix_and_org_prefix_stripped(self, rows):
        index, ambiguous = build_index(rows)
        assert match_arena_name("z-ai/glm-5.2:free", index, ambiguous) is None
        # but a real hit via bare tail
        assert match_arena_name("thinkingmachines/inkling:free", index,
                                ambiguous) == "inkling"

    def test_date_suffix_and_spaces_normalized(self, rows):
        index, ambiguous = build_index(rows)
        # arena "Inkling Small" (space) vs id tail inkling-small-20260730
        assert match_arena_name(
            "thinkingmachines/inkling-small-20260730", index, ambiguous
        ) == "Inkling Small"

    def test_org_prefix_candidate_form(self, rows):
        index, ambiguous = build_index(rows)
        assert match_arena_name("nvidia/nemotron-3-super-120b-a12b:free",
                                index, ambiguous) == \
            "nvidia-nemotron-3-super-120b-a12b"

    def test_quantization_tag_stripped_from_arena_side(self, rows):
        index, ambiguous = build_index(rows)
        assert match_arena_name("nvidia/nemotron-3-ultra-550b-a55b:free",
                                index, ambiguous) == \
            "nvidia-nemotron-3-ultra-550b-a55b-nvfp4"

    def test_variant_tag_it_stripped_from_model_side(self, rows):
        index, ambiguous = build_index(rows)
        assert match_arena_name("google/gemma-4-31b-it:free", index,
                                ambiguous) == "gemma-4-31b"

    def test_version_number_never_stripped(self):
        # glm-5.2 must NOT degrade to a "glm-5" entry — different model
        index, _ = build_index([{"name": "glm-5", "organization": None, "rank": 7}])
        assert match_arena_name("z-ai/glm-5.2:free", index) is None

    def test_ambiguous_forms_never_match(self, rows):
        index, ambiguous = build_index(rows)
        # gpt-4o and gpt-4o-latest both normalize to "gpt-4o"
        assert match_arena_name("openai/gpt-4o:free", index, ambiguous) is None


class TestApplyArenaRanks:
    def test_ranks_set_only_for_openrouter(self, rows):
        models = [
            Model(provider_id="openrouter", model_id="thinkingmachines/inkling:free", free=True),
            Model(provider_id="tokenrouter", model_id="thinkingmachines/inkling", free=True),
            Model(provider_id="openrouter", model_id="stealth/union-alpha", free=True),
        ]
        matched, skipped = apply_arena_ranks(models, rows)
        assert matched == 1
        assert skipped == 0
        assert models[0].arena_rank == 85
        assert models[1].arena_rank is None  # no cross-provider leak
        assert models[2].arena_rank is None  # not on the leaderboard

    def test_ambiguous_match_counted_as_skip(self, rows):
        models = [
            Model(provider_id="openrouter", model_id="openai/gpt-4o:free", free=True),
        ]
        matched, skipped = apply_arena_ranks(models, rows)
        assert (matched, skipped) == (0, 1)


class TestRefreshArena:
    def test_success_saves_artifact(self, payload, tmp_path, monkeypatch):
        monkeypatch.setattr(lmarena, "MIN_ENTRIES", 5)
        http = FakeHttpClient({ARENA_URL: payload})
        rows, warnings = refresh_arena(http, tmp_path / "arena.json")
        assert not warnings
        assert len(rows) == 8
        saved = json.loads((tmp_path / "arena.json").read_text(encoding="utf-8"))
        assert saved["source"] == ARENA_URL
        assert saved["fetched"]
        assert [m["rank"] for m in saved["models"]] == sorted(
            m["rank"] for m in saved["models"]
        )

    def test_rsc_header_sent(self, payload, tmp_path, monkeypatch):
        monkeypatch.setattr(lmarena, "MIN_ENTRIES", 5)
        http = FakeHttpClient({ARENA_URL: payload})
        refresh_arena(http, tmp_path / "arena.json")
        # FakeHttpClient records hits; headers are asserted implicitly by
        # the real client seam test in test_collectors (get_text(headers=)).
        assert http.hits == [ARENA_URL]

    def test_fetch_failure_with_no_artifact_writes_empty(self, tmp_path):
        http = FakeHttpClient({})  # nothing programmed -> None
        rows, warnings = refresh_arena(http, tmp_path / "arena.json")
        assert rows == []
        assert any("fetch failed" in w for w in warnings)
        saved = json.loads((tmp_path / "arena.json").read_text(encoding="utf-8"))
        assert saved["models"] == []
        assert saved["fetched"] is None

    def test_parse_failure_keeps_previous_artifact(self, payload, tmp_path, monkeypatch):
        monkeypatch.setattr(lmarena, "MIN_ENTRIES", 100)  # 8 rows < 100 -> fail
        path = tmp_path / "arena.json"
        path.write_text(json.dumps({
            "source": ARENA_URL, "fetched": "2026-09-01",
            "models": [{"name": "old", "organization": None, "rank": 1}],
        }), encoding="utf-8")
        http = FakeHttpClient({ARENA_URL: payload})
        rows, warnings = refresh_arena(http, path)
        assert rows == [{"name": "old", "organization": None, "rank": 1}]
        assert any("expected" in w for w in warnings)
        # previous artifact untouched (fail-soft)
        assert load_arena(path) == [{"name": "old", "organization": None,
                                     "rank": 1}]
