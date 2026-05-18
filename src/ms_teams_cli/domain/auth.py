"""Authentication protocols for ms-teams-cli."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenProvider(Protocol):
    """Protocol for Graph API token providers."""

    def get_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        ...


@runtime_checkable
class ChatTokenProvider(Protocol):
    """Protocol for Teams Chat Service token providers."""

    def get_token(self) -> tuple[str, str]:
        """Return a chat token and chat service URL, refreshing if necessary."""
        ...
