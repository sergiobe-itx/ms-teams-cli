"""Tests for login/logout CLI commands."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ms_teams_cli.domain.exceptions import AuthenticationError
from ms_teams_cli.presentation.cli import app

runner = CliRunner()


def test_login_command_success() -> None:
    with patch("ms_teams_cli.infrastructure.auth.msal_provider.MsalGraphTokenProvider") as mock_cls:
        mock_provider = MagicMock()
        mock_provider.login.return_value = "access-token"
        mock_cls.return_value = mock_provider

        result = runner.invoke(app, ["login"])

        assert result.exit_code == 0
        assert "Login successful" in result.output


def test_login_command_failure() -> None:
    with patch("ms_teams_cli.infrastructure.auth.msal_provider.MsalGraphTokenProvider") as mock_cls:
        mock_provider = MagicMock()
        mock_provider.login.side_effect = AuthenticationError("not logged in")
        mock_cls.return_value = mock_provider

        result = runner.invoke(app, ["login"])

        assert result.exit_code == 1


def test_logout_command_success() -> None:
    with patch("ms_teams_cli.infrastructure.auth.msal_provider.MsalGraphTokenProvider") as mock_cls:
        mock_provider = MagicMock()
        mock_cls.return_value = mock_provider

        result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        assert "Logged out" in result.output
        mock_provider.logout.assert_called_once()
