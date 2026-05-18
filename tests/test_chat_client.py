"""Tests for Teams Chat Service HTTP client."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ms_teams_cli.domain.exceptions import ChatServiceAPIError
from ms_teams_cli.infrastructure.chat import ChatServiceClient

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


class FakeChatProvider:
    def __init__(
        self,
        token: str = "token123",
        service_url: str = "https://chat.example.test",
        renewed_token: str = "renewed456",
    ) -> None:
        self.token: str = token
        self.service_url: str = service_url
        self.renewed_token: str = renewed_token
        self.get_token_calls: int = 0
        self.renew_calls: int = 0

    def get_token(self) -> tuple[str, str]:
        self.get_token_calls += 1
        return self.token, self.service_url

    def renew(self) -> tuple[str, str]:
        self.renew_calls += 1
        return self.renewed_token, self.service_url


def test_chat_client_uses_authentication_header(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="GET", url=url, json={"conversations": []})

    data = ChatServiceClient(token_provider=provider).get(url)

    assert data == {"conversations": []}
    request = httpx_mock.get_requests()[0]
    assert request.headers["Authentication"] == "skypetoken=token123"


def test_chat_client_does_not_use_authorization_header(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="GET", url=url, json={"conversations": []})

    _ = ChatServiceClient(token_provider=provider).get(url)

    request = httpx_mock.get_requests()[0]
    assert "Authorization" not in request.headers


def test_chat_client_retries_on_401(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider(token="expired", renewed_token="fresh")
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="GET", url=url, status_code=401)
    httpx_mock.add_response(method="GET", url=url, json={"conversations": [{"id": "c1"}]})

    data = ChatServiceClient(token_provider=provider).get(url)

    assert data == {"conversations": [{"id": "c1"}]}
    assert provider.get_token_calls == 1
    assert provider.renew_calls == 1
    requests = httpx_mock.get_requests()
    assert requests[0].headers["Authentication"] == "skypetoken=expired"
    assert requests[1].headers["Authentication"] == "skypetoken=fresh"


def test_chat_client_retries_on_403(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider(token="expired", renewed_token="fresh")
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="GET", url=url, status_code=403)
    httpx_mock.add_response(method="GET", url=url, json={"conversations": []})

    _ = ChatServiceClient(token_provider=provider).get(url)

    assert provider.renew_calls == 1
    assert len(httpx_mock.get_requests()) == 2


def test_chat_client_raises_on_error(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="GET", url=url, status_code=500, text="boom")

    with pytest.raises(ChatServiceAPIError) as exc_info:
        _ = ChatServiceClient(token_provider=provider).get(url)

    assert exc_info.value.status_code == 500
    assert exc_info.value.url == url
    assert "boom" in str(exc_info.value)


def test_chat_client_post_uses_authentication_header(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="POST", url=url, json={"ok": True})

    data = ChatServiceClient(token_provider=provider).post(url, {"hello": "world"})

    assert data == {"ok": True}
    request = httpx_mock.get_requests()[0]
    assert request.headers["Authentication"] == "skypetoken=token123"
    assert request.headers["Content-Type"] == "application/json"


def test_chat_client_post_does_not_use_authorization_header(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="POST", url=url, json={"ok": True})

    _ = ChatServiceClient(token_provider=provider).post(url, {"hello": "world"})

    request = httpx_mock.get_requests()[0]
    assert "Authorization" not in request.headers


def test_chat_client_post_retries_on_401(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider(token="expired", renewed_token="fresh")
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="POST", url=url, status_code=401)
    httpx_mock.add_response(method="POST", url=url, json={"id": "created"})

    data = ChatServiceClient(token_provider=provider).post(url, {"body": "payload"})

    assert data == {"id": "created"}
    requests = httpx_mock.get_requests()
    assert requests[0].headers["Authentication"] == "skypetoken=expired"
    assert requests[1].headers["Authentication"] == "skypetoken=fresh"


def test_chat_client_post_returns_empty_dict_for_empty_body(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="POST", url=url, status_code=200, content=b"")

    data = ChatServiceClient(token_provider=provider).post(url, {"body": "payload"})

    assert data == {}


def test_chat_client_exposes_service_url() -> None:
    provider = FakeChatProvider(service_url="https://emea.ng.msg.teams.microsoft.com")

    service_url = ChatServiceClient(token_provider=provider).get_service_url()

    assert service_url == "https://emea.ng.msg.teams.microsoft.com"


def test_chat_client_wraps_non_dict_get_json(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="GET", url=url, json=[{"id": "c1"}])

    data = ChatServiceClient(token_provider=provider).get(url)

    assert data == {"value": [{"id": "c1"}]}


def test_chat_client_wraps_non_dict_post_json(httpx_mock: HTTPXMock) -> None:
    provider = FakeChatProvider()
    url = "https://chat.example.test/v1/users/ME/conversations"
    httpx_mock.add_response(method="POST", url=url, json=[{"id": "created"}])

    data = ChatServiceClient(token_provider=provider).post(url, {"payload": "x"})

    assert data == {"value": [{"id": "created"}]}
