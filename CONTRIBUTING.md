# Contributing to TokenMiner

Thanks for helping mine deals, verify facts and preserve history.

## Ground rules

- **No secrets.** Never commit API keys, cookies, passwords or tokens. The
  pipeline only uses public, unauthenticated endpoints.
- **No fabrication.** Every number (credits, rate limits, context windows)
  must be something you actually saw on an official page. If you can't verify
  it, leave it `null` or mark it `uncertain`/`community` — never guess.
- **No scraping abuse.** Requests go through `tokenminer/utils/http.py`
  (timeout, retries, ≥1s politeness per host). Don't add bypasses for
  Cloudflare, logins or rate limits, and never automate signups or claims.

## Adding a provider

1. Add an entry to `data/providers.yaml` (SPEC §7 schema). Tier-2/3 providers
   get `collector: generic` plus `watch_urls` for change detection.
2. Verified free offers go into `data/seeds/offers.yaml` with the full Offer
   schema (SPEC §8) and a `source_url` you actually fetched.
3. Run `python -m tokenminer validate` then `python -m tokenminer` and check
   the regenerated README/docs.

## Adding an offer

Only offers from official sources (pricing/docs/API pages) may be
`confidence: official`. Community leads must be verified on the official page
first; if unverifiable, record them as `confidence: community` +
`status: uncertain`.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
pytest -q
python -m tokenminer
```

Tests are offline: all network is mocked through the single `HttpClient`
seam (`tokenminer/utils/http.py`). Keep it that way.
