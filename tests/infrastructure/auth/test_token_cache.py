"""Tests for token cache components."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _future_iso(seconds: int = 3600) -> str:
    dt = datetime.now(UTC) + timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _past_iso(seconds: int = 3600) -> str:
    dt = datetime.now(UTC) - timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_token_cache_saves_and_loads_graph_token(tmp_path: Path) -> None:
    from ms_teams_cli.infrastructure.auth import TokenCache

    cache = TokenCache(tmp_path / "graph-token.json")

    cache.save("graph-token", _future_iso())

    assert cache.load() == "graph-token"
    assert json.loads(cache.path.read_text()) == {
        "token": "graph-token",
        "expiresOn": json.loads(cache.path.read_text())["expiresOn"],
    }


def test_token_cache_returns_none_when_expired(tmp_path: Path) -> None:
    from ms_teams_cli.infrastructure.auth import TokenCache

    cache = TokenCache(tmp_path / "graph-token.json")
    cache.save("expired-token", _past_iso())

    assert cache.load() is None


def test_token_cache_returns_none_when_within_margin(tmp_path: Path) -> None:
    from ms_teams_cli.infrastructure.auth import TOKEN_MARGIN, TokenCache

    cache = TokenCache(tmp_path / "graph-token.json")
    cache.save("almost-expired", _future_iso(TOKEN_MARGIN - 100))

    assert cache.load() is None


def test_token_cache_uses_xdg_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAMS_TOKEN_CACHE", raising=False)
    monkeypatch.delenv("TEAMS_SKYPE_TOKEN_CACHE", raising=False)

    import ms_teams_cli.infrastructure.auth.token_cache as token_cache_module

    monkeypatch.setattr(
        token_cache_module,
        "_CACHE_DIR",
        tmp_path / ".cache" / "ms-teams-cli",
    )
    cache = token_cache_module.TokenCache()

    cache.save("graph-token", _future_iso())

    assert cache.path == tmp_path / ".cache" / "ms-teams-cli" / "graph-token.json"
    assert cache.path.exists()


def test_token_cache_hit_avoids_subprocess_call(tmp_path: Path) -> None:
    from unittest.mock import patch

    from ms_teams_cli.infrastructure.auth import AzGraphTokenProvider, TokenCache

    cache = TokenCache(tmp_path / "graph-token.json")
    cache.save("cached-token", _future_iso())

    with patch("ms_teams_cli.infrastructure.auth.az_provider.subprocess.run") as run:
        token = AzGraphTokenProvider(cache=cache).get_token()

    assert token == "cached-token"
    run.assert_not_called()
