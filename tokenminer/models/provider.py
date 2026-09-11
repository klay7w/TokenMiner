"""Provider schema (SPEC §7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utils.time import empty_str_to_none

Category = Literal["router", "official", "candidate"]
ProviderStatus = Literal["active", "uncertain", "unavailable"]


class Provider(BaseModel):
    """An AI API provider / router (seed registry entry, enriched by collectors)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: Category = "official"
    description: str = ""
    official_url: str | None = None
    pricing_url: str | None = None
    docs_url: str | None = None
    models_url: str | None = None
    signup_url: str | None = None
    api_base_url: str | None = None
    api_compatibility: list[str] = Field(default_factory=list)
    requires_account: bool = True
    status: ProviderStatus = "active"
    last_checked: object = None
    last_verified: object = None
    sources: list[str] = Field(default_factory=list)
    # Tier 2/3 providers without a dedicated collector:
    collector: str | None = None
    watch_urls: list[str] = Field(default_factory=list)

    _dates = field_validator("last_checked", "last_verified", mode="before")(
        empty_str_to_none
    )
