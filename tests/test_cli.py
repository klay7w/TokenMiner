"""CLI behavior tests (offline)."""

from __future__ import annotations

from tokenminer.__main__ import main


def test_no_args_defaults_to_help_not_crash():
    # `python -m tokenminer --help` exits 0
    assert main(["--help"]) == 0


def test_unknown_command_exits_2():
    assert main(["frobnicate"]) == 2


def test_validate_runs_against_repo_data():
    # data/ ships in the repo; validate must load all of it (exit 0)
    assert main(["validate"]) == 0
