"""Collector base: ABC + result container (SPEC §12–14)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..models import Model, Offer, Provider
from ..utils.http import HttpClient


@dataclass
class CollectorResult:
    """What a collector learned this run."""

    models: list[Model] = field(default_factory=list)          # replaces provider's models
    offers: list[Offer] = field(default_factory=list)           # keyed by id
    provider_updates: dict[str, object] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)              # informational
    warnings: list[str] = field(default_factory=list)           # logged, never fatal


class Collector(ABC):
    """Base class for provider collectors. One instance per run."""

    provider_id: str = ""

    @abstractmethod
    def collect(self, http: HttpClient, provider: Provider) -> CollectorResult:
        """Fetch provider data. Failures -> warnings in the result, not exceptions."""
