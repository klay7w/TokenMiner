"""Small date/time helpers (UTC-based, ISO strings at the edges)."""

from __future__ import annotations

from datetime import date, datetime, timezone


def today() -> date:
    """Current UTC date."""
    return datetime.now(timezone.utc).date()


def to_iso(d: date | None) -> str | None:
    """date -> ISO string (None stays None)."""
    return d.isoformat() if d else None


def parse_date(value: str | date | None) -> date | None:
    """Parse an ISO date string; '' / None / garbage -> None."""
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def empty_str_to_none(value: object) -> object:
    """Pydantic before-validator: '' -> None, ISO str -> date."""
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        return parse_date(value)
    return value


def days_ago(d: date | None) -> int | None:
    """Whole days between ``d`` and today (None-safe)."""
    if d is None:
        return None
    return (today() - d).days
