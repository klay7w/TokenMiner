"""Model schema (SPEC §9)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utils.time import empty_str_to_none


class Model(BaseModel):
    """A model exposed by a provider.

    Prices are USD per token exactly as reported by the source API (display
    layers may convert to $/1M tokens). Facts without official reliable
    information stay None — never guessed from model names (SPEC §9).
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    model_id: str
    name: str = ""
    developer: str = ""
    model_type: list[str] = Field(default_factory=lambda: ["text"])
    context_length: int | None = None
    max_output_tokens: int | None = None
    input_price: float | None = None
    output_price: float | None = None
    free: bool = False
    free_variant: str | None = None
    rate_limit: str | None = None
    supports_tools: bool | None = None
    supports_vision: bool | None = None
    supports_reasoning: bool | None = None
    model_url: str = ""
    source_url: str = ""
    last_checked: object = None
    last_verified: object = None

    _dates = field_validator("last_checked", "last_verified", mode="before")(
        empty_str_to_none
    )
