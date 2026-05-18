"""Tests for GraphChatRepository adapter."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ms_teams_cli.domain.entities import ChatType
from ms_teams_cli.infrastructure.graph import GraphChatRepository, GraphClient

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


def _repo() -> GraphChatRepository:
    return GraphChatRepository(graph_client=GraphClient(token_provider=FakeProvider()))


def test_list_chats_maps_types(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me"},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://graph.microsoft.com/v1.0/me/chats"
            "?$expand=members,lastMessagePreview"
            "&$top=50"
            "&$orderby=lastMessagePreview/createdDateTime desc"
        ),
        json={
            "value": [
                {"id": "c1", "chatType": "oneOnOne", "members": []},
                {"id": "c2", "chatType": "group", "members": []},
                {"id": "c3", "chatType": "meeting", "members": []},
            ]
        },
    )

    chats = _repo().list_chats()

    assert [chat.chat_type for chat in chats] == [
        ChatType.ONE_TO_ONE,
        ChatType.GROUP,
        ChatType.MEETING,
    ]


def test_list_chats_filters_by_type(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me"},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://graph.microsoft.com/v1.0/me/chats"
            "?$expand=members,lastMessagePreview"
            "&$top=50"
            "&$orderby=lastMessagePreview/createdDateTime desc"
        ),
        json={
            "value": [
                {"id": "c1", "chatType": "oneOnOne", "members": []},
                {"id": "c2", "chatType": "group", "members": []},
                {"id": "c3", "chatType": "meeting", "members": []},
            ]
        },
    )

    chats = _repo().list_chats(chat_type=ChatType.GROUP)

    assert len(chats) == 1
    assert chats[0].id == "c2"
    assert chats[0].chat_type is ChatType.GROUP


def test_list_chats_display_name_1on1(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me-123"},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://graph.microsoft.com/v1.0/me/chats"
            "?$expand=members,lastMessagePreview"
            "&$top=50"
            "&$orderby=lastMessagePreview/createdDateTime desc"
        ),
        json={
            "value": [
                {
                    "id": "chat-123",
                    "chatType": "oneOnOne",
                    "members": [
                        {"userId": "me-123", "displayName": "Me"},
                        {"userId": "other-456", "displayName": "Alice"},
                    ],
                }
            ]
        },
    )

    chats = _repo().list_chats()

    assert chats[0].display_name == "Alice"


def test_list_unread_detects_unread(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me"},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://graph.microsoft.com/v1.0/me/chats"
            "?$expand=members,lastMessagePreview"
            "&$top=200"
            "&$orderby=lastMessagePreview/createdDateTime desc"
        ),
        json={
            "value": [
                {
                    "id": "unread",
                    "chatType": "group",
                    "members": [],
                    "viewpoint": {"lastMessageReadDateTime": "2026-05-18T10:00:00Z"},
                    "lastMessagePreview": {"createdDateTime": "2026-05-18T10:05:00Z"},
                },
                {
                    "id": "read",
                    "chatType": "group",
                    "members": [],
                    "viewpoint": {"lastMessageReadDateTime": "2026-05-18T10:05:00Z"},
                    "lastMessagePreview": {"createdDateTime": "2026-05-18T10:05:00Z"},
                },
                {
                    "id": "noviewpoint",
                    "chatType": "group",
                    "members": [],
                    "lastMessagePreview": {"createdDateTime": "2026-05-18T10:06:00Z"},
                },
            ]
        },
    )

    chats = _repo().list_unread()

    assert [chat.id for chat in chats] == ["unread", "noviewpoint"]


def test_list_unread_empty_when_no_messages(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me"},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://graph.microsoft.com/v1.0/me/chats"
            "?$expand=members,lastMessagePreview"
            "&$top=200"
            "&$orderby=lastMessagePreview/createdDateTime desc"
        ),
        json={
            "value": [
                {
                    "id": "empty",
                    "chatType": "group",
                    "members": [],
                    "viewpoint": {"lastMessageReadDateTime": ""},
                }
            ]
        },
    )

    chats = _repo().list_unread()

    assert chats == []


def test_list_unread_filters_by_type(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me"},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://graph.microsoft.com/v1.0/me/chats"
            "?$expand=members,lastMessagePreview"
            "&$top=200"
            "&$orderby=lastMessagePreview/createdDateTime desc"
        ),
        json={
            "value": [
                {
                    "id": "one",
                    "chatType": "oneOnOne",
                    "members": [],
                    "lastMessagePreview": {"createdDateTime": "2026-05-18T10:05:00Z"},
                },
                {
                    "id": "group",
                    "chatType": "group",
                    "members": [],
                    "lastMessagePreview": {"createdDateTime": "2026-05-18T10:06:00Z"},
                },
            ]
        },
    )

    chats = _repo().list_unread(chat_type=ChatType.GROUP)

    assert [chat.id for chat in chats] == ["group"]


def test_get_messages_filters_system_messages(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1/messages?$top=30",
        json={
            "value": [
                {
                    "id": "5",
                    "createdDateTime": "2026-05-18T10:05:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "text", "content": "five"},
                },
                {
                    "id": "4",
                    "createdDateTime": "2026-05-18T10:04:00Z",
                    "from": {"user": {"displayName": "System"}},
                    "body": {"contentType": "text", "content": "system"},
                    "eventMessageDetail": {"event": "rename"},
                },
                {
                    "id": "3",
                    "createdDateTime": "2026-05-18T10:03:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "html", "content": "<p>three</p>"},
                },
                {
                    "id": "2",
                    "createdDateTime": "2026-05-18T10:02:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "unknownFutureValue", "content": "ignored"},
                },
                {
                    "id": "1",
                    "createdDateTime": "2026-05-18T10:01:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "text", "content": "one"},
                },
            ]
        },
    )

    messages = _repo().get_messages("chat-1")

    assert len(messages) == 3
    assert [message.id for message in messages] == ["1", "3", "5"]


def test_get_messages_chronological_order(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1/messages?$top=30",
        json={
            "value": [
                {
                    "id": "newest",
                    "createdDateTime": "2026-05-18T10:03:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "text", "content": "third"},
                },
                {
                    "id": "middle",
                    "createdDateTime": "2026-05-18T10:02:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "text", "content": "second"},
                },
                {
                    "id": "oldest",
                    "createdDateTime": "2026-05-18T10:01:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "text", "content": "first"},
                },
            ]
        },
    )

    messages = _repo().get_messages("chat-1")

    assert [message.id for message in messages] == ["oldest", "middle", "newest"]


def test_get_messages_strips_html(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1/messages?$top=30",
        json={
            "value": [
                {
                    "id": "m1",
                    "createdDateTime": "2026-05-18T10:01:00Z",
                    "from": {"user": {"displayName": "Alice"}},
                    "body": {"contentType": "html", "content": "<p>Hello</p>"},
                }
            ]
        },
    )

    messages = _repo().get_messages("chat-1")

    assert messages[0].content == "Hello"
    assert messages[0].message_type == "RichText/Html"


def test_send_message_text(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1/messages",
        json={"id": "msg-123"},
    )

    message_id = _repo().send_message("chat-1", "hi")

    assert message_id == "msg-123"
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert json.loads(requests[0].content.decode()) == {
        "body": {"content": "hi", "contentType": "text"}
    }


def test_send_message_html(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1/messages",
        json={"id": "msg-456"},
    )

    _ = _repo().send_message("chat-1", "<b>bold</b>")

    request = httpx_mock.get_requests()[0]
    assert json.loads(request.content.decode()) == {
        "body": {"content": "<b>bold</b>", "contentType": "html"}
    }


def test_resolve_chat_name_returns_topic(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1?$expand=members",
        json={"id": "chat-1", "topic": "Project Alpha", "members": []},
    )

    name = _repo().resolve_chat_name("chat-1")

    assert name == "Project Alpha"


def test_resolve_chat_name_fallback_members(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me/chats/chat-1?$expand=members",
        json={
            "id": "chat-1",
            "members": [
                {"userId": "me-123", "displayName": "Me"},
                {"userId": "other-456", "displayName": "Alice"},
            ],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://graph.microsoft.com/v1.0/me",
        json={"id": "me-123"},
    )

    name = _repo().resolve_chat_name("chat-1")

    assert name == "Alice"
