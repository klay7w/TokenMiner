"""Thin wrapper: `python scripts/update.py` == `python -m tokenminer update`."""

from tokenminer.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(["update"]))
