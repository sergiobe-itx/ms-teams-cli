"""Tests for Microsoft Graph HTTP client."""
from __future__ import annotations

from datetime import date
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


def test_get_success(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me/joinedTeams",
        json={"value": [{"id": "t1"}]},
    )

    data = GraphClient(token_provider=provider).get(
        "https://graph.microsoft.com/v1.0/me/joinedTeams"
    )

    assert data == {"value": [{"id": "t1"}]}
    assert provider.get_token_calls == 1
    assert provider.renew_calls == 0


def test_get_retries_on_401(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider(token="expired-token", renewed_token="fresh-token")
    url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
    httpx_mock.add_response(method="GET", url=url, status_code=401)
    httpx_mock.add_response(method="GET", url=url, json={"value": [{"id": "t1"}]})

    data = GraphClient(token_provider=provider).get(url)

    assert data == {"value": [{"id": "t1"}]}
    assert provider.get_token_calls == 1
    assert provider.renew_calls == 1
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].headers["Authorization"] == "Bearer expired-token"
    assert requests[1].headers["Authorization"] == "Bearer fresh-token"


def test_get_raises_graph_api_error_on_404(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    url = "https://graph.microsoft.com/v1.0/me/unknown"
    httpx_mock.add_response(
        method="GET",
        url=url,
        status_code=404,
        json={"error": {"message": "Missing resource"}},
    )

    with pytest.raises(GraphAPIError) as exc_info:
        _ = GraphClient(token_provider=provider).get(url)

    assert exc_info.value.status_code == 404
    assert exc_info.value.url == url
    assert "Missing resource" in str(exc_info.value)


def test_get_raises_graph_api_error_on_500(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
    httpx_mock.add_response(
        method="GET",
        url=url,
        status_code=500,
        json={"error": {"message": "Server exploded"}},
    )

    with pytest.raises(GraphAPIError) as exc_info:
        _ = GraphClient(token_provider=provider).get(url)

    assert exc_info.value.status_code == 500
    assert exc_info.value.url == url
    assert "Server exploded" in str(exc_info.value)


def test_paginate_single_page(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    url = "https://graph.microsoft.com/v1.0/me/messages"
    httpx_mock.add_response(
        method="GET",
        url=url,
        json={"value": [{"id": "1"}, {"id": "2"}]},
    )

    items = list(GraphClient(token_provider=provider).paginate(url))

    assert items == [{"id": "1"}, {"id": "2"}]
    assert len(httpx_mock.get_requests()) == 1


def test_paginate_multi_page(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    url = "https://graph.microsoft.com/v1.0/me/messages"
    next_url = "https://graph.microsoft.com/v1.0/me/messages?$skiptoken=abc"
    httpx_mock.add_response(
        method="GET",
        url=url,
        json={"value": [{"id": "1"}], "@odata.nextLink": next_url},
    )
    httpx_mock.add_response(method="GET", url=next_url, json={"value": [{"id": "2"}]})

    items = list(GraphClient(token_provider=provider).paginate(url, max_pages=5))

    assert items == [{"id": "1"}, {"id": "2"}]
    assert len(httpx_mock.get_requests()) == 2


def test_paginate_stops_at_max_pages(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    first = "https://graph.microsoft.com/v1.0/me/messages"
    second = "https://graph.microsoft.com/v1.0/me/messages?page=2"
    third = "https://graph.microsoft.com/v1.0/me/messages?page=3"
    httpx_mock.add_response(
        method="GET",
        url=first,
        json={"value": [{"id": "1"}], "@odata.nextLink": second},
    )
    httpx_mock.add_response(
        method="GET",
        url=second,
        json={"value": [{"id": "2"}], "@odata.nextLink": third},
    )

    items = list(GraphClient(token_provider=provider).paginate(first, max_pages=2))

    assert items == [{"id": "1"}, {"id": "2"}]
    assert len(httpx_mock.get_requests()) == 2


def test_paginate_stops_before_date(httpx_mock: HTTPXMock) -> None:
    provider = FakeProvider()
    first = "https://graph.microsoft.com/v1.0/me/messages"
    second = "https://graph.microsoft.com/v1.0/me/messages?page=2"
    httpx_mock.add_response(
        method="GET",
        url=first,
        json={
            "value": [
                {"id": "1", "createdDateTime": "2023-12-31T23:59:59Z"},
                {"id": "2", "createdDateTime": "2023-12-30T12:00:00Z"},
            ],
            "@odata.nextLink": second,
        },
    )

    items = list(
        GraphClient(token_provider=provider).paginate(
            first,
            max_pages=5,
            stop_before=date(2024, 1, 1).isoformat(),
        )
    )

    assert items == [
        {"id": "1", "createdDateTime": "2023-12-31T23:59:59Z"},
        {"id": "2", "createdDateTime": "2023-12-30T12:00:00Z"},
    ]
    assert len(httpx_mock.get_requests()) == 1
