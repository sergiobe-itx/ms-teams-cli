"""HTTP client for the Teams Chat Service (Skype-based API)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import httpx

from ms_teams_cli.domain.exceptions import ChatServiceAPIError

if TYPE_CHECKING:
    from ms_teams_cli.domain.ports import ChatTokenProvider


@runtime_checkable
class _RenewableChatTokenProvider(Protocol):
    """Chat token provider with explicit renewal support."""

    def get_token(self) -> tuple[str, str]:
        """Return the current chat token and service URL."""
        ...

    def renew(self) -> tuple[str, str]:
        """Refresh and return a new chat token and service URL."""
        ...


class ChatServiceClient:
    """Thin httpx-based client for the Teams Chat Service API."""

    def __init__(self, token_provider: ChatTokenProvider) -> None:
        self._provider: ChatTokenProvider = token_provider

    def get_service_url(self) -> str:
        """Return the current chat service base URL."""
        _, chat_service_url = self._provider.get_token()
        return chat_service_url

    def get(self, url: str) -> dict[str, object]:
        """GET url with Authentication: skypetoken={token} header."""
        token, _ = self._provider.get_token()
        response = httpx.get(url, headers=_headers(token), timeout=30)
        if response.status_code in (401, 403):
            token, _ = self._renew_token()
            response = httpx.get(url, headers=_headers(token), timeout=30)
        if response.is_error:
            raise ChatServiceAPIError(
                f"Chat API HTTP {response.status_code} — {response.text[:200]}\n  URL: {url}",
                status_code=response.status_code,
                url=url,
            )
        payload = cast("object", response.json())
        return _as_json_dict(payload)

    def post(self, url: str, body: dict[str, object]) -> dict[str, object]:
        """POST to url with Authentication: skypetoken={token} header."""
        token, _ = self._provider.get_token()
        response = httpx.post(url, json=body, headers=_post_headers(token), timeout=30)
        if response.status_code in (401, 403):
            token, _ = self._renew_token()
            response = httpx.post(url, json=body, headers=_post_headers(token), timeout=30)
        if response.is_error:
            raise ChatServiceAPIError(
                f"Chat API POST HTTP {response.status_code} — {response.text[:200]}\n  URL: {url}",
                status_code=response.status_code,
                url=url,
            )
        if not response.content:
            return {}
        payload = cast("object", response.json())
        return _as_json_dict(payload)

    def _renew_token(self) -> tuple[str, str]:
        provider = self._provider
        if isinstance(provider, _RenewableChatTokenProvider):
            return provider.renew()
        return provider.get_token()


def _headers(token: str) -> dict[str, str]:
    return {
        "Authentication": f"skypetoken={token}",
        "Accept": "application/json",
    }


def _post_headers(token: str) -> dict[str, str]:
    return {
        "Authentication": f"skypetoken={token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _as_json_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {"value": value}
