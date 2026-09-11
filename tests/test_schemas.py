"""Schema tests for Provider / Offer / Model (SPEC §38)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tokenminer.models import Model, Offer, Provider


class TestProviderSchema:
    def test_valid_minimal(self):
        p = Provider(id="x", name="X")
        assert p.category == "official"
        assert p.status == "active"
        assert p.api_compatibility == []
        assert p.last_verified is None

    def test_full(self):
        p = Provider(
            id="openrouter", name="OpenRouter", category="router",
            api_compatibility=["openai"], requires_account=True,
            status="active", sources=["https://openrouter.ai"],
            collector="generic", watch_urls=["https://example.com"],
        )
        assert p.collector == "generic"

    def test_bad_category_rejected(self):
        with pytest.raises(ValidationError):
            Provider(id="x", name="X", category="mega")

    def test_bad_status_rejected(self):
        with pytest.raises(ValidationError):
            Provider(id="x", name="X", status="paused")

    def test_unknown_field_rejected(self):
        with pytest.raises(ValidationError):
            Provider(id="x", name="X", colour="blue")

    def test_empty_date_coerces_to_none(self):
        p = Provider(id="x", name="X", last_checked="", last_verified="")
        assert p.last_checked is None
        assert p.last_verified is None

    def test_iso_date_string_parsed(self):
        p = Provider(id="x", name="X", last_checked="2026-09-11")
        assert str(p.last_checked) == "2026-09-11"


class TestOfferSchema:
    def test_valid_minimal(self):
        o = Offer(id="a", provider_id="p", title="T", type="signup_credit")
        assert o.status == "active"
        assert o.confidence == "unknown"
        assert o.value is None
        assert o.recurring is False

    def test_bad_type_rejected(self):
        with pytest.raises(ValidationError):
            Offer(id="a", provider_id="p", title="T", type="mega_discount")

    def test_bad_confidence_rejected(self):
        with pytest.raises(ValidationError):
            Offer(id="a", provider_id="p", title="T", type="trial",
                  confidence="guaranteed")

    def test_bad_status_rejected(self):
        with pytest.raises(ValidationError):
            Offer(id="a", provider_id="p", title="T", type="trial",
                  status="paused")

    def test_dates_coerced(self):
        o = Offer(
            id="a", provider_id="p", title="T", type="trial",
            end_date="2026-12-31", first_seen="", last_checked="2026-09-11",
        )
        assert str(o.end_date) == "2026-12-31"
        assert o.first_seen is None

    def test_roundtrip_json(self):
        o = Offer(id="a", provider_id="p", title="T", type="free_tier",
                  value=5, currency="USD", end_date="2026-12-31")
        restored = Offer.model_validate_json(o.model_dump_json())
        assert restored == o


class TestModelSchema:
    def test_valid_minimal(self):
        m = Model(provider_id="openrouter", model_id="openai/gpt-4o")
        assert m.model_type == ["text"]
        assert m.free is False
        assert m.context_length is None  # unknown stays None, never guessed

    def test_context_must_be_int(self):
        with pytest.raises(ValidationError):
            Model(provider_id="p", model_id="m", context_length="huge")

    def test_caps_flags_default_none(self):
        m = Model(provider_id="p", model_id="m")
        assert m.supports_tools is None
        assert m.supports_vision is None
        assert m.supports_reasoning is None
