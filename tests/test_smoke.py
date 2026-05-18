"""Smoke tests for package importability and version."""
from __future__ import annotations

from ms_teams_cli import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"
