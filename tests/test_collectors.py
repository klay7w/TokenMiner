"""Collector tests against trimmed real fixtures (offline, mocked HTTP)."""

from __future__ import annotations

import json

from tokenminer.collectors.generic import GenericCollector
from tokenminer.collectors.openrouter import OpenRouterCollector
from tokenminer.collectors.tokenrouter import TokenRouterCollector
from tokenminer.models import Provider
from conftest import FakeHttpClient

OR_API = "https://openrouter.ai/api/v1/models"
TR_MODELS = "https://tokenrouter.com/models"
TR_DOCS = "https://tokenrouter.com/docs"
TR_BLOG = "https://tokenrouter.com/blog"


class TestOpenRouterCollector:
    def test_parses_real_fixture(self, openrouter_fixture):
        http = FakeHttpClient({OR_API: json.dumps(openrouter_fixture)})
        provider = Provider(id="openrouter", name="OpenRouter")
        result = OpenRouterCollector().collect(http, provider)

        assert len(result.models) == 8
        free = [m for m in result.models if m.free]
        assert len(free) == 5
        assert all(m.model_id.endswith(":free") for m in free)
        # developer derived from id prefix (API has no developer field)
        by_id = {m.model_id: m for m in result.models}
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].developer == "inclusionai"
        # capability flags mapped honestly from supported_parameters
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].supports_tools is True
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].supports_reasoning is True
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].supports_vision is True
        assert by_id["inclusionai/ling-3.0-flash-sante:free"].supports_vision is False
        # context + prices
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].context_length == 262144
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].input_price == 0.0
        assert by_id["deepseek/deepseek-v4.1-flash"].input_price == 3e-07
        # model_url built from canonical slug
        assert by_id["inclusionai/ling-3.0-flash-vl:free"].model_url.startswith(
            "https://openrouter.ai/inclusionai/"
        )
        # paid sibling annotated with its free variant (when present in data)
        assert (by_id["nvidia/nemotron-3.5-lightning"].free_variant
                == "nvidia/nemotron-3.5-lightning:free")
        assert by_id["inclusionai/ling-3.0-flash-fin"].free_variant is None
        assert by_id["deepseek/deepseek-v4.1-flash"].free_variant is None

    def test_free_tier_offer_created(self, openrouter_fixture):
        http = FakeHttpClient({OR_API: json.dumps(openrouter_fixture)})
        provider = Provider(id="openrouter", name="OpenRouter")
        result = OpenRouterCollector().collect(http, provider)
        assert len(result.offers) == 1
        offer = result.offers[0]
        assert offer.type == "free_tier"
        assert offer.confidence == "official"
        assert offer.claim_url == "https://openrouter.ai/models?max_price=0"
        assert offer.source_url == OR_API
        assert "5 models" in offer.title
        assert result.provider_updates["status"] == "active"

    def test_api_failure_is_warning_not_crash(self):
        http = FakeHttpClient({})  # nothing programmed -> fetch returns None
        provider = Provider(id="openrouter", name="OpenRouter")
        result = OpenRouterCollector().collect(http, provider)
        assert result.models == []
        assert result.warnings

    def test_no_hardcoded_free_list(self, openrouter_fixture):
        """If the API stopped returning a free model, it must not reappear."""
        fixture = json.loads(json.dumps(openrouter_fixture))
        fixture["data"] = [m for m in fixture["data"] if not m["id"].endswith(":free")]
        http = FakeHttpClient({OR_API: json.dumps(fixture)})
        provider = Provider(id="openrouter", name="OpenRouter")
        result = OpenRouterCollector().collect(http, provider)
        assert not any(m.free for m in result.models)
        assert result.offers == []  # no free models -> no free-tier offer


class TestTokenRouterCollector:
    def test_parses_real_fixture(self, tokenrouter_html):
        http = FakeHttpClient({
            TR_MODELS: tokenrouter_html,
            TR_DOCS: "<html><body>docs shell</body></html>",
            TR_BLOG: "<html><body>blog shell</body></html>",
        })
        provider = Provider(id="tokenrouter", name="TokenRouter")
        result = TokenRouterCollector().collect(http, provider)

        assert len(result.models) == 6
        free = [m for m in result.models if m.free]
        assert [m.model_id for m in free] == ["z-ai/glm-5.3-free"]
        glm = free[0]
        assert glm.developer == "智谱"  # provider name as published (Chinese)
        assert glm.model_type == ["text"]
        assert glm.context_length is None  # never guessed
        assert glm.supports_tools is None  # page does not say
        assert glm.model_url == "https://tokenrouter.com/models/z-ai/glm-5.3-free/"
        # embedding + image models mapped honestly
        by_id = {m.model_id: m for m in result.models}
        assert "embedding" in by_id["google/gemini-embedding-2"].model_type
        assert "image" in by_id["openai/gpt-image-2.5-sunburst"].model_type

    def test_free_models_offer(self, tokenrouter_html):
        http = FakeHttpClient({
            TR_MODELS: tokenrouter_html, TR_DOCS: "", TR_BLOG: "",
        })
        provider = Provider(id="tokenrouter", name="TokenRouter")
        result = TokenRouterCollector().collect(http, provider)
        assert len(result.offers) == 1
        offer = result.offers[0]
        assert offer.type == "free_tier"
        assert offer.claim_url == TR_MODELS
        assert offer.confidence == "official"

    def test_no_credit_offer_without_evidence(self, tokenrouter_html):
        """Docs/blog are JS shells with no credit keywords -> no credit offer."""
        http = FakeHttpClient({
            TR_MODELS: tokenrouter_html,
            TR_DOCS: "<html><body>API reference only</body></html>",
            TR_BLOG: "<html><body>release notes</body></html>",
        })
        provider = Provider(id="tokenrouter", name="TokenRouter")
        result = TokenRouterCollector().collect(http, provider)
        assert [o.type for o in result.offers] == ["free_tier"]
        assert any("no credit/promotion evidence" in n for n in result.notes)

    def test_credit_evidence_reported_in_notes(self, tokenrouter_html):
        http = FakeHttpClient({
            TR_MODELS: tokenrouter_html,
            TR_DOCS: "<html><body>New users get free credits</body></html>",
            TR_BLOG: "<html><body></body></html>",
        })
        provider = Provider(id="tokenrouter", name="TokenRouter")
        result = TokenRouterCollector().collect(http, provider)
        assert any("credit evidence keywords" in n for n in result.notes)


class TestGenericCollector:
    def _provider(self, urls):
        return Provider(id="groq", name="Groq", collector="generic",
                        watch_urls=list(urls))

    def test_change_detection(self, tmp_path):
        state = tmp_path / "generic_state.json"
        page = "<html><body>Free tier with 30 RPM limits</body></html>"
        http = FakeHttpClient({"https://x.example/a": page})
        collector = GenericCollector(state)

        r1 = collector.collect(http, self._provider(["https://x.example/a"]))
        assert any("now watching" in n for n in r1.notes)
        assert r1.provider_updates["last_verified"] is not None

        # same content -> no change note
        http2 = FakeHttpClient({"https://x.example/a": page})
        r2 = collector.collect(http2, self._provider(["https://x.example/a"]))
        assert r2.notes == []

        # content changed -> flagged
        http3 = FakeHttpClient({
            "https://x.example/a": "<html><body>Free tier with 60 RPM limits</body></html>",
        })
        r3 = collector.collect(http3, self._provider(["https://x.example/a"]))
        assert any("watch page changed" in n for n in r3.notes)

        # state survives and is JSON
        data = json.loads(state.read_text(encoding="utf-8"))
        assert "https://x.example/a" in data["groq"]
        assert "free" in data["groq"]["https://x.example/a"]["keywords"]

    def test_unreachable_watch_url_does_not_crash(self, tmp_path):
        http = FakeHttpClient({})  # nothing programmed
        collector = GenericCollector(tmp_path / "state.json")
        result = collector.collect(
            http, self._provider(["https://down.example/x"])
        )
        assert result.warnings
        assert "last_verified" not in result.provider_updates

    def test_js_shell_page_is_hashed_without_error(self, tmp_path):
        shell = '<html><body><div id="root"></div><script>app()</script></body></html>'
        http = FakeHttpClient({"https://shell.example/": shell})
        collector = GenericCollector(tmp_path / "state.json")
        result = collector.collect(http, self._provider(["https://shell.example/"]))
        assert result.warnings == []
        assert result.provider_updates.get("last_verified") is not None
