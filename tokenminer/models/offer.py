"""Offer schema (SPEC §8)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from ..utils.time import empty_str_to_none

OfferType = Literal[
    "free_tier",
    "signup_credit",
    "recurring_credit",
    "free_model",
    "trial",
    "promotion",
    "student",
    "developer_program",
    "unknown",
]
OfferStatus = Literal["active", "uncertain", "expired", "unavailable"]
Confidence = Literal["official", "high", "medium", "community", "unknown"]


class Offer(BaseModel):
    """A free deal offered by a provider. Offers are separate from providers."""

    model_config = ConfigDict(extra="forbid")

    id: str
    provider_id: str
    title: str
    type: OfferType
    description: str = ""
    value: float | None = None
    currency: str | None = None
    free_tokens: str | None = None
    recurring: bool = False
    new_users_only: bool = False
    requires_payment_method: bool | None = None
    requires_phone: bool | None = None
    requires_student_verification: bool = False
    region_limit: str | None = None
    start_date: object = None
    end_date: object = None
    claim_url: str = ""
    source_url: str = ""
    status: OfferStatus = "active"
    confidence: Confidence = "unknown"
    first_seen: object = None
    last_checked: object = None
    last_verified: object = None
    stale: bool = False

    _dates = field_validator(
        "start_date", "end_date", "first_seen", "last_checked", "last_verified",
        mode="before",
    )(empty_str_to_none)
