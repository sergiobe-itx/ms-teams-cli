"""Domain exceptions for ms-teams-cli."""
from __future__ import annotations


class TeamsError(Exception):
    """Base exception for all ms-teams-cli errors."""


class AuthenticationError(TeamsError):
    """Raised when authentication fails."""


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired and cannot be renewed."""


class APIError(TeamsError):
    """Raised when an API call fails with an HTTP error."""

    def __init__(self, message: str, status_code: int, url: str) -> None:
        super().__init__(message)
        self.status_code: int = status_code
        self.url: str = url


class GraphAPIError(APIError):
    """Raised when a Microsoft Graph API call fails."""


class ChatServiceAPIError(APIError):
    """Raised when a Teams Chat Service API call fails."""
