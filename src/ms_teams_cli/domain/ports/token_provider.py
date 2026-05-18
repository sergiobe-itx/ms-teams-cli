"""Token provider protocols for ms-teams-cli."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenProvider(Protocol):
    """Protocol for Graph API token providers."""

    def get_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        ...


@runtime_checkable
class GraphTokenProvider(TokenProvider, Protocol):
    """Graph token provider with renewal support."""

    def renew(self) -> str:
        """Refresh and return a new access token."""
        ...
