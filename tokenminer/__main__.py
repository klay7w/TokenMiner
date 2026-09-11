"""CLI entry point (SPEC §30).

``python -m tokenminer``            -> update (default)
``python -m tokenminer update``     -> full update pipeline
``python -m tokenminer validate``   -> schema-check all data files
``python -m tokenminer generate``   -> regenerate docs from existing data
"""

from __future__ import annotations

import sys

from .pipeline import run_generate, run_update, run_validate

USAGE = "usage: python -m tokenminer [update|validate|generate]"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "update"
    if command in ("-h", "--help"):
        print(USAGE)
        return 0
    if command == "update":
        return run_update()
    if command == "validate":
        return run_validate()
    if command == "generate":
        return run_generate()
    print(f"unknown command: {command}\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
