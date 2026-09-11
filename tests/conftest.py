"""Shared test fixtures. ALL network is faked through the HttpClient seam."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class FakeFetchResult:
    def __init__(self, url: str, status: int, text: str) -> None:
        self.url = url
        self.final_url = url
        self.status = status
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class FakeHttpClient:
    """Drop-in stand-in for tokenminer.utils.http.HttpClient (no network)."""

    def __init__(self, pages: dict[str, str | tuple[int, str]] | None = None) -> None:
        self.pages = pages or {}
        self.hits: list[str] = []

    def fetch(self, url: str) -> FakeFetchResult | None:
        self.hits.append(url)
        if url not in self.pages:
            return None
        page = self.pages[url]
        if isinstance(page, tuple):
            status, text = page
        else:
            status, text = 200, page
        return FakeFetchResult(url, status, text)

    def get_text(self, url: str) -> str | None:
        result = self.fetch(url)
        return result.text if result is not None and result.ok else None

    def get_json(self, url: str):
        text = self.get_text(url)
        if text is None:
            return None
        try:
            return json.loads(text)
        except ValueError:
            return None


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def openrouter_fixture() -> dict:
    return json.loads(load_fixture("openrouter_models.json"))


@pytest.fixture
def tokenrouter_html() -> str:
    return load_fixture("tokenrouter_models.html")


def d(day: int) -> date:
    """Deterministic date helper (2026-09-01 + day)."""
    from datetime import timedelta

    return date(2026, 9, 1) + timedelta(days=day)
