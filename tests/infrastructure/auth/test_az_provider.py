"""Tests for az CLI token providers."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from ms_teams_cli.domain.exceptions import AuthenticationError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_httpx import HTTPXMock


def _future_iso(seconds: int = 3600) -> str:
    dt = datetime.now(UTC) + timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_az_graph_provider_gets_token_via_subprocess(tmp_path: Path) -> None:
    from ms_teams_cli.infrastructure.auth import AzGraphTokenProvider, TokenCache

    cache = TokenCache(tmp_path / "graph-token.json")
    result = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "accessToken": "fresh-graph-token",
                "expiresOn": "2027-01-01 12:00:00.123456",
            }
        ),
        stderr="",
    )

    with patch(
        "ms_teams_cli.infrastructure.auth.az_provider.subprocess.run",
        return_value=result,
    ) as run:
        token = AzGraphTokenProvider(cache=cache).get_token()

    assert token == "fresh-graph-token"
    assert cache.load() == "fresh-graph-token"
    assert json.loads(cache.path.read_text()) == {
        "token": "fresh-graph-token",
        "expiresOn": "2027-01-01T12:00:00Z",
    }
    run.assert_called_once()


def test_az_graph_provider_raises_auth_error_when_az_fails(tmp_path: Path) -> None:
    from ms_teams_cli.infrastructure.auth import AzGraphTokenProvider, TokenCache

    cache = TokenCache(tmp_path / "graph-token.json")
    result = MagicMock(returncode=1, stdout="", stderr="login failed")

    with (
        patch(
            "ms_teams_cli.infrastructure.auth.az_provider.subprocess.run",
            return_value=result,
        ),
        pytest.raises(AuthenticationError, match="az login required"),
    ):
            _ = AzGraphTokenProvider(cache=cache).get_token()


def test_az_chat_provider_performs_two_step_exchange(
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    from ms_teams_cli.infrastructure.auth import AzChatTokenProvider, ChatTokenCache

    cache = ChatTokenCache(tmp_path / "chat-token.json")
    result = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "accessToken": "aad-token",
                "expiresOn": "2027-01-01 12:00:00.123456",
            }
        ),
        stderr="",
    )
    httpx_mock.add_response(
        method="POST",
        url="https://authsvc.teams.microsoft.com/v1.0/authz",
        json={
            "tokens": {"skypeToken": "skype-token", "expiresIn": 3600},
            "regionGtms": {"chatService": "https://chat.example.test"},
        },
    )

    with patch(
        "ms_teams_cli.infrastructure.auth.az_provider.subprocess.run",
        return_value=result,
    ) as run:
        token, url = AzChatTokenProvider(cache=cache).get_token()

    assert (token, url) == ("skype-token", "https://chat.example.test")
    assert cache.load() == ("skype-token", "https://chat.example.test")
    assert json.loads(cache.path.read_text())["skypeToken"] == "skype-token"
    assert json.loads(cache.path.read_text())["chatService"] == "https://chat.example.test"
    run.assert_called_once()
    request = httpx_mock.get_requests()[0]
    assert request.headers["Authorization"] == "Bearer aad-token"
    assert json.loads(request.content.decode()) == {
        "resourceUrl": "https://api.spaces.skype.com"
    }
