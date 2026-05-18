"""Chained token provider — tries providers in order, falls back on AuthenticationError."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ms_teams_cli.domain.exceptions import AuthenticationError

if TYPE_CHECKING:
    from ms_teams_cli.domain.ports.token_provider import TokenProvider


class ChainedTokenProvider:
    """Try each provider in order; return first success or raise AuthenticationError."""

    def __init__(self, providers: list[TokenProvider]) -> None:
        self._providers = providers

    def get_token(self) -> str:
        """Try each provider in order; raise if all fail."""
        last_error: AuthenticationError | None = None
        for provider in self._providers:
            try:
                return provider.get_token()
            except AuthenticationError as exc:
                last_error = exc
        raise AuthenticationError(
            "Authentication failed. Run: ms-teams login\n\n"
            "Alternatively: az login --scope https://graph.microsoft.com/.default"
        ) from last_error

    def renew(self) -> str:
        """Renew token by trying each provider in order."""
        last_error: AuthenticationError | None = None
        for provider in self._providers:
            try:
                return provider.renew()
            except AuthenticationError as exc:
                last_error = exc
        raise AuthenticationError(
            "Token renewal failed. Run: ms-teams login\n\n"
            "Alternatively: az login --scope https://graph.microsoft.com/.default"
        ) from last_error
