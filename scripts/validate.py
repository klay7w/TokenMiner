"""Thin wrapper: `python scripts/validate.py` == `python -m tokenminer validate`."""

from tokenminer.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(["validate"]))
