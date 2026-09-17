"""OpenRouter collector (SPEC §12).

Pulls the public model list from https://openrouter.ai/api/v1/models (no auth),
detects ``:free`` variants dynamically (no hardcoded model lists), maps fields
honestly, and maintains a provider-level free-tier offer.
"""

from __future__ import annotations

from ..models import Model, Offer
from ..utils.http import HttpClient
from ..utils.time import today
from .base import Collector, CollectorResult

API_URL = "https://openrouter.ai/api/v1/models"
RANKED_API_URL = API_URL + "?order=top_weekly"  # data[] order IS the rank
CLAIM_URL = "https://openrouter.ai/models?max_price=0"
LIMITS_DOC = "https://openrouter.ai/docs/api-reference/limits"
FREE_OFFER_ID = "openrouter-free-models"

# input/output modality tokens we pass through into model_type
_MODILITY_MAP = {"text": "text", "image": "image", "audio": "audio",
                 "video": "video", "file": "file"}


def _parse_price(value: object) -> float | None:
    """OpenRouter prices are USD-per-token strings ('0' = free)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class OpenRouterCollector(Collector):
    provider_id = "openrouter"

    def collect(self, http: HttpClient, provider) -> CollectorResult:  # type: ignore[override]
        result = CollectorResult()
        data = http.get_json(API_URL)
        entries = data.get("data") if isinstance(data, dict) else None
        if not isinstance(entries, list) or not entries:
            result.warnings.append("OpenRouter: models API returned no data")
            return result

        now = today()
        models: list[Model] = []
        free_ids: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            model = self._to_model(entry, now)
            models.append(model)
            if model.free:
                free_ids.add(model.model_id)
        # annotate paid models whose :free sibling exists
        for m in models:
            if not m.free and f"{m.model_id}:free" in free_ids:
                m.free_variant = f"{m.model_id}:free"

        # weekly usage ranking (SPEC §40 tier 2): data[] order is the rank
        usage = self._usage_ranks(http)
        if not usage:
            result.warnings.append("OpenRouter: weekly usage ranking unavailable")
        for m in models:
            m.usage_rank = usage.get(m.model_id)

        result.models = models
        free_models = [m for m in models if m.free]
        result.provider_updates = {
            "status": "active",
            "last_checked": now,
            "last_verified": now,
            "models_url": "https://openrouter.ai/models",
        }
        if free_models:
            result.offers = [Offer(
                id=FREE_OFFER_ID,
                provider_id=self.provider_id,
                title=f"OpenRouter Free Models ({len(free_models)} models)",
                type="free_tier",
                description=(
                    f"{len(free_models)} models are priced $0 per token, most "
                    f"carrying a ':free' id suffix. Free variants are subject to platform "
                    f"free-usage rate limits; current numbers are rendered "
                    f"dynamically on the limits page, so they are not recorded "
                    f"as fixed values. See {LIMITS_DOC}."
                ),
                recurring=False,
                new_users_only=False,
                requires_payment_method=False,
                claim_url=CLAIM_URL,
                source_url=API_URL,
                status="active",
                confidence="official",
                first_seen=None,  # preserved from previous data when merging
                last_checked=now,
                last_verified=now,
            )]
        result.notes.append(
            f"OpenRouter: {len(models)} models, {len(free_models)} free"
        )
        return result

    def _usage_ranks(self, http: HttpClient) -> dict[str, int]:
        """model_id -> weekly usage rank (1 = most used). {} on failure."""
        ranked = http.get_json(RANKED_API_URL)
        entries = ranked.get("data") if isinstance(ranked, dict) else None
        if not isinstance(entries, list) or not entries:
            return {}
        return {
            entry.get("id"): rank
            for rank, entry in enumerate(entries, 1)
            if isinstance(entry, dict) and entry.get("id")
        }

    def _to_model(self, entry: dict, checked: object) -> Model:
        model_id: str = entry["id"]
        slug = entry.get("canonical_slug") or model_id
        developer = entry.get("developer") or model_id.split("/", 1)[0]
        architecture = entry.get("architecture") or {}
        input_modalities = architecture.get("input_modalities") or []
        output_modalities = architecture.get("output_modalities") or []
        model_type = _model_type(input_modalities, output_modalities)
        pricing = entry.get("pricing") or {}
        top = entry.get("top_provider") or {}
        params = entry.get("supported_parameters") or []
        input_price = _parse_price(pricing.get("prompt"))
        output_price = _parse_price(pricing.get("completion"))
        free = model_id.endswith(":free") or (
            input_price == 0 and output_price == 0
        )
        return Model(
            provider_id=self.provider_id,
            model_id=model_id,
            name=entry.get("name") or model_id,
            developer=developer,
            model_type=model_type,
            context_length=_int_or_none(entry.get("context_length")),
            max_output_tokens=_int_or_none(top.get("max_completion_tokens")),
            input_price=input_price,
            output_price=output_price,
            free=free,
            rate_limit=None,  # exact free-tier numbers not published in the API
            supports_tools="tools" in params,
            supports_vision="image" in input_modalities,
            supports_reasoning="reasoning" in params,
            model_url=f"https://openrouter.ai/{slug}",
            source_url=API_URL,
            last_checked=checked,
            last_verified=checked,
        )


def _model_type(input_modalities: list, output_modalities: list) -> list[str]:
    kinds: list[str] = []
    for modality in list(input_modalities) + list(output_modalities):
        kind = _MODILITY_MAP.get(str(modality))
        if kind and kind not in kinds:
            kinds.append(kind)
    if "text" in kinds:
        kinds.remove("text")
        kinds.insert(0, "text")  # text-first, stable ordering
    return kinds or ["text"]


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
