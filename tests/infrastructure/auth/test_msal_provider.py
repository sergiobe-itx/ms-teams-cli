"""Tests for MsalGraphTokenProvider."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from ms_teams_cli.domain.exceptions import AuthenticationError
from ms_teams_cli.infrastructure.auth.msal_provider import MsalGraphTokenProvider

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_msal_app():
    with patch("ms_teams_cli.infrastructure.auth.msal_provider.msal") as mock_msal:
        mock_app = MagicMock()
        mock_msal.PublicClientApplication.return_value = mock_app
        mock_msal.SerializableTokenCache.return_value = MagicMock(has_state_changed=False)
        yield mock_app


def test_get_token_raises_when_no_cache(mock_msal_app: MagicMock, tmp_path: Path) -> None:
    mock_msal_app.get_accounts.return_value = []
    provider = MsalGraphTokenProvider(cache_path=tmp_path / "nonexistent.json")

    with pytest.raises(AuthenticationError, match="ms-teams login"):
        provider.get_token()


def test_get_token_returns_token_on_silent_success(
    mock_msal_app: MagicMock, tmp_path: Path
) -> None:
    mock_msal_app.get_accounts.return_value = [{"mock": "account"}]
    mock_msal_app.acquire_token_silent.return_value = {"access_token": "test-token-123"}
    provider = MsalGraphTokenProvider(cache_path=tmp_path / "cache.json")

    result = provider.get_token()

    assert result == "test-token-123"


def test_get_token_raises_when_silent_fails(mock_msal_app: MagicMock, tmp_path: Path) -> None:
    mock_msal_app.get_accounts.return_value = [{"mock": "account"}]
    mock_msal_app.acquire_token_silent.return_value = {"error": "no_tokens"}
    provider = MsalGraphTokenProvider(cache_path=tmp_path / "cache.json")

    with pytest.raises(AuthenticationError, match="ms-teams login"):
        provider.get_token()


def test_login_calls_device_flow_and_returns_token(
    mock_msal_app: MagicMock, tmp_path: Path
) -> None:
    mock_msal_app.initiate_device_flow.return_value = {
        "user_code": "XXXX",
        "verification_uri": "https://microsoft.com/devicelogin",
    }
    mock_msal_app.acquire_token_by_device_flow.return_value = {"access_token": "login-token"}
    provider = MsalGraphTokenProvider(cache_path=tmp_path / "cache.json")

    result = provider.login()

    assert result == "login-token"
    mock_msal_app.initiate_device_flow.assert_called_once()
    mock_msal_app.acquire_token_by_device_flow.assert_called_once()


def test_login_raises_when_device_flow_fails(mock_msal_app: MagicMock, tmp_path: Path) -> None:
    mock_msal_app.initiate_device_flow.return_value = {"error": "no_user_code"}
    provider = MsalGraphTokenProvider(cache_path=tmp_path / "cache.json")

    with pytest.raises(AuthenticationError, match="Device flow initiation failed"):
        provider.login()


def test_logout_removes_cache_file(mock_msal_app: MagicMock, tmp_path: Path) -> None:
    cache_file = tmp_path / "msal_cache.json"
    cache_file.write_text('{"some": "data"}', encoding="utf-8")
    provider = MsalGraphTokenProvider(cache_path=cache_file)

    provider.logout()

    assert not cache_file.exists()


def test_logout_does_nothing_when_no_cache(mock_msal_app: MagicMock, tmp_path: Path) -> None:
    cache_path = tmp_path / "nonexistent_xyz_abc.json"
    provider = MsalGraphTokenProvider(cache_path=cache_path)

    provider.logout()

    assert not cache_path.exists()
