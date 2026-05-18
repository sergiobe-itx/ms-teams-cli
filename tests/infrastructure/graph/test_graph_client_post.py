"""Tests for GraphClient.post() method."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ms_teams_cli.domain.exceptions import GraphAPIError
from ms_teams_cli.infrastructure.graph import GraphClient

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


class FakeProvider:
    def __init__(self, token: str = "token-1", renewed_token: str = "token-2") -> None:
        self.token: str = token
        self.renewed_token: str = renewed_token
        self.get_token_calls: int = 0
        self.renew_calls: int = 0

    def get_token(self) -> str:
        self.get_token_calls += 1
        return self.token

    def renew(self) -> str:
        self.renew_calls += 1
        return self.renewed_token


def test_post_success(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    url = "https://graph.microsoft.com/v1.0/me/messages"
    httpx_mock.add_response(
        method="POST",
        url=url,
        status_code=201,
        json={"id": "msg-1"},
    )

    data = GraphClient(token_provider=provider).post(url, {"subject": "Test"})

    assert data == {"id": "msg-1"}
    assert provider.get_token_calls == 1
    assert provider.renew_calls == 0


def test_post_retries_on_401(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider(token="expired-token", renewed_token="fresh-token")
    url = "https://graph.microsoft.com/v1.0/me/messages"
    httpx_mock.add_response(method="POST", url=url, status_code=401)
    httpx_mock.add_response(
        method="POST",
        url=url,
        status_code=201,
        json={"id": "ok"},
    )

    data = GraphClient(token_provider=provider).post(url, {"subject": "Test"})

    assert data == {"id": "ok"}
    assert provider.get_token_calls == 1
    assert provider.renew_calls == 1
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].headers["Authorization"] == "Bearer expired-token"
    assert requests[1].headers["Authorization"] == "Bearer fresh-token"


def test_post_raises_on_error(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    url = "https://graph.microsoft.com/v1.0/me/messages"
    httpx_mock.add_response(
        method="POST",
        url=url,
        status_code=403,
        json={"error": {"message": "Access denied"}},
    )

    with pytest.raises(GraphAPIError) as exc_info:
        _ = GraphClient(token_provider=provider).post(url, {"subject": "Test"})

    assert exc_info.value.status_code == 403
    assert exc_info.value.url == url
    assert "Access denied" in str(exc_info.value)
