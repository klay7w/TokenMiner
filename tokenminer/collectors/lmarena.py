"""LMArena leaderboard collector (auxiliary data source, SPEC §40).

Fetches the public text leaderboard from llmarena.ai, persists it as
data/arena.json, and matches entries to OpenRouter model ids so free
models can be ranked by a recognized external benchmark.

Transport detail: the leaderboard page is a Next.js app — a plain GET
returns the HTML shell. Sending ``RSC: 1`` returns the flight payload
(text/x-component) instead, which embeds the leaderboard ``entries``
array as flat JSON objects. The payload is NOT valid JSON overall, so
entries are extracted with a tolerant anchored regex. Fail-soft like
every collector: failures produce warnings, never exceptions.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Model
from ..store import ARENA_PATH, load_arena, save_arena
from ..utils.http import HttpClient
from ..utils.time import today

LEADERBOARD_URL = "https://llmarena.ai/leaderboard/text"
RSC_HEADERS = {"RSC": "1"}
MIN_ENTRIES = 100  # sanity threshold; the real leaderboard has ~400 rows

# Leaderboard ``entries``: flat objects with ``rank`` first. The plots'
# ``modelRatings`` objects start with ``modelDisplayName`` instead, so this
# anchor cannot cross-match them.
_ENTRY_RE = re.compile(
    r'\{"rank":(\d+),"rankUpper":\d+,"rankLower":\d+,'
    r'"modelKey":"[^"]*","modelDisplayName":"([^"]*)"'
)
# Capability rows elsewhere in the payload carry the organization
# (best-effort provenance; some rows omit it).
_ORG_RE = re.compile(r'"organization":"([^"]*)","provider":"[^"]*","publicName":"([^"]*)"')

# Trailing date-version tags stripped from either side of a match.
_DATE_TAIL_RE = re.compile(r"[-_.]?20\d{2}[-_.]?\d{2}[-_.]?\d{2}$")
# Variant tags safe to strip from EITHER side. Version numbers are
# deliberately NOT strippable: ``glm-5.2`` -> ``glm-5`` would be a
# different model, not a variant of it.
_STRIP_TOKENS = frozenset({
    "it", "instruct", "chat", "latest", "preview", "base", "free",
    "omni", "thinking", "reasoning", "vl", "vision",
    "bf16", "fp8", "nvfp4",
})


def parse_payload(text: str) -> list[dict]:
    """Extract ranked leaderboard rows ``[{name, organization, rank}]``
    sorted by rank (best first). Duplicate display names keep their best
    (lowest) rank. Returns [] when nothing parses — callers decide if that
    is a failure (see :func:`refresh_arena`)."""
    seen: dict[str, tuple[str, int]] = {}  # lowercase key -> (raw name, best rank)
    for m in _ENTRY_RE.finditer(text):
        rank, name = int(m.group(1)), m.group(2)
        key = name.lower()
        current = seen.get(key)
        if current is None or rank < current[1]:
            seen[key] = (name, rank)
    if not seen:
        return []
    orgs = {
        public.lower().replace(" ", "-"): org
        for org, public in _ORG_RE.findall(text)
    }
    return [
        {
            "name": name,
            "organization": orgs.get(normalize(name)),
            "rank": rank,
        }
        for name, rank in sorted(seen.values(), key=lambda kv: kv[1])
    ]


def normalize(name: str) -> str:
    """Canonical form for matching: lowercase, spaces to '-', then strip
    trailing date-version and variant tags iteratively. Applied to BOTH
    the OpenRouter id tail and the arena display name, so both sides meet
    at the same canonical form."""
    s = name.lower().strip()
    s = re.sub(r"\s+", "-", s)
    while True:
        m = _DATE_TAIL_RE.search(s)
        if m:
            s = s[: m.start()]
            continue
        head, sep, tail = s.rpartition("-")
        if sep and tail in _STRIP_TOKENS:
            s = head
            continue
        return s


def build_index(
    rows: list[dict],
) -> tuple[dict[str, tuple[str, int]], set[str]]:
    """normalized form -> (raw arena name, best rank), plus the set of
    forms that collapsed from multiple distinct arena names (ambiguous —
    never matched, SPEC §40)."""
    best: dict[str, tuple[str, int]] = {}
    raw_names: dict[str, set[str]] = {}
    for row in rows:
        key = normalize(row["name"])
        raw_names.setdefault(key, set()).add(row["name"].lower())
        current = best.get(key)
        if current is None or row["rank"] < current[1]:
            best[key] = (row["name"], row["rank"])
    ambiguous = {k for k, names in raw_names.items() if len(names) > 1}
    return best, ambiguous


def arena_candidates(model_id: str) -> list[str]:
    """Canonical forms for an OpenRouter model id: the bare tail (org
    prefix dropped, ':free' and variant tags stripped) and the
    ``<org>-<tail>`` form — arena prefixes some developers (e.g.
    ``nvidia-nemotron-3-super-120b-a12b``)."""
    s = model_id.lower()
    if s.endswith(":free"):
        s = s[: -len(":free")]
    org, _, tail = s.partition("/")
    forms = [normalize(tail)]
    if org:
        forms.append(normalize(f"{org}-{tail}"))
    return forms


def match_arena_name(
    model_id: str,
    index: dict[str, tuple[str, int]],
    ambiguous: set[str] | None = None,
) -> str | None:
    """Exact canonical match of an OpenRouter id against the leaderboard
    index. Ambiguous forms never match (SPEC §40). No fuzzy matching."""
    ambiguous = ambiguous or set()
    for form in arena_candidates(model_id):
        if form in ambiguous:
            continue
        hit = index.get(form)
        if hit is not None:
            return hit[0]
    return None


def apply_arena_ranks(models: list[Model], rows: list[dict]) -> tuple[int, int]:
    """Set ``arena_rank`` on OpenRouter models matched against leaderboard
    rows. Other providers are skipped (ranks never leak across providers).
    Returns (matched count, ambiguous-skip count)."""
    index, ambiguous = build_index(rows)
    rank_by_name: dict[str, int] = {}
    for row in rows:
        key = row["name"].lower()
        if key not in rank_by_name or row["rank"] < rank_by_name[key]:
            rank_by_name[key] = row["rank"]
    matched = skipped = 0
    for m in models:
        if m.provider_id != "openrouter":
            continue
        hit = match_arena_name(m.model_id, index, ambiguous)
        if hit is None:
            if any(f in ambiguous for f in arena_candidates(m.model_id)):
                skipped += 1
            continue
        m.arena_rank = rank_by_name[hit.lower()]
        matched += 1
    return matched, skipped


def refresh_arena(
    http: HttpClient, path: Path = ARENA_PATH
) -> tuple[list[dict], list[str]]:
    """Fetch the leaderboard, persist data/arena.json, return rows.

    Fail-soft (SPEC §40): a fetch or parse failure keeps the previous
    artifact and returns its rows (last known state); when no artifact
    exists an empty one is written. Warnings are returned, not raised."""
    warnings: list[str] = []
    text = http.get_text(LEADERBOARD_URL, headers=RSC_HEADERS)
    rows: list[dict] = []
    if text is None:
        warnings.append("LMArena: leaderboard fetch failed")
    else:
        rows = parse_payload(text)
        if len(rows) < MIN_ENTRIES:
            warnings.append(
                f"LMArena: parsed {len(rows)} entries, expected >= {MIN_ENTRIES}"
            )
            rows = []
    if rows:
        save_arena(rows, LEADERBOARD_URL, today().isoformat(), path)
        return rows, warnings
    previous = load_arena(path)
    if previous is None:
        save_arena([], LEADERBOARD_URL, None, path)
        previous = []
    return previous, warnings
