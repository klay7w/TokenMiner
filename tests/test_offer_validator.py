"""OfferValidator tests with a fake HTTP layer (SPEC §33, §25–26)."""

from __future__ import annotations

from datetime import date, timedelta

from tokenminer.models import Offer
from tokenminer.validators.offer_validator import OfferValidator
from conftest import FakeHttpClient

TODAY = date(2026, 9, 11)


def _offer(**kw) -> Offer:
    base = dict(
        id="o1", provider_id="p", title="Offer", type="signup_credit",
        claim_url="https://example.com/claim", source_url="https://example.com/src",
        status="active", confidence="official",
        last_verified=TODAY - timedelta(days=1), last_checked=TODAY - timedelta(days=1),
    )
    base.update(kw)
    return Offer(**base)


def _http(source_text="Get $5 free credit on signup", source_status=200,
          claim_status=200):
    pages = {
        "https://example.com/claim": (claim_status, "claim page"),
        "https://example.com/src": (source_status, source_text),
    }
    return FakeHttpClient(pages)


def _run(offer, http):
    offers, warnings = OfferValidator().validate_offers([offer], http)
    return offers[0], warnings


def test_successful_verification_bumps_last_verified():
    offer, _ = _run(_offer(), _http())
    assert offer.status == "active"
    assert offer.last_verified == TODAY
    assert offer.last_checked == TODAY
    assert offer.stale is False


def test_end_date_passed_marks_expired():
    offer = _offer(end_date=TODAY - timedelta(days=1))
    offer, _ = _run(offer, _http())
    assert offer.status == "expired"
    assert offer.last_checked == TODAY  # still checked


def test_expired_signal_on_source_marks_expired():
    offer, _ = _run(_offer(), _http(source_text="This promotion has ended"))
    assert offer.status == "expired"


def test_lone_expired_word_is_not_an_expiration_signal():
    """'ended' inside unrelated prose (e.g. 'recommended') must not expire."""
    offer = _offer()
    offer, _ = _run(offer, _http(
        source_text="We recommended extended plans. Your session has expired. "
                   "Sign up now for a free tier."))
    assert offer.status == "active"
    assert offer.last_verified == TODAY  # still verified: free keyword present


def test_source_unreachable_does_not_verify_or_expire():
    offer, warnings = _run(_offer(), _http(source_status=404))
    assert offer.status == "active"  # never auto-expire from one failure
    assert offer.last_verified != TODAY
    assert any("unreachable" in w for w in warnings)


def test_keyword_missing_does_not_bump_last_verified():
    offer, warnings = _run(_offer(), _http(source_text="Everything costs money"))
    assert offer.status == "active"
    assert offer.last_verified != TODAY
    assert any("not verified" in w for w in warnings)


def test_stale_after_7_days():
    old = TODAY - timedelta(days=8)
    offer = _offer(last_verified=old)
    offer, _ = _run(offer, _http())  # re-verifies today
    assert offer.stale is False
    # now simulate not re-verifying (source fails keyword check)
    offer = _offer(last_verified=old)
    offer, _ = _run(offer, _http(source_text="paid product"))
    assert offer.stale is True
    assert offer.status == "active"  # stale != expired


def test_uncertain_after_30_days_without_verification():
    offer = _offer(last_verified=TODAY - timedelta(days=31))
    offer, _ = _run(offer, _http(source_text="premium only"))
    assert offer.status == "uncertain"
    assert offer.stale is True


def test_expired_offers_are_not_revalidated():
    offer = _offer(status="expired")
    http = _http()
    offer, _ = _run(offer, http)
    assert "https://example.com/src" not in http.hits  # skipped entirely
    assert offer.status == "expired"


def test_offers_returned_in_place_sorted():
    offers = [_offer(id="b"), _offer(id="a")]
    result, _ = OfferValidator().validate_offers(offers, _http())
    assert [o.id for o in result] == ["b", "a"]
