"""Tests for chat application service, classifier, display, and CLI."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from typer.testing import CliRunner

import ms_teams_cli.application.chats as chats_module
import ms_teams_cli.infrastructure.az_provider as az_provider_module
import ms_teams_cli.infrastructure.chat_client as chat_client_module
import ms_teams_cli.infrastructure.token_cache as token_cache_module
import ms_teams_cli.presentation.cli as cli_module
import ms_teams_cli.presentation.formatters as formatters_module
from ms_teams_cli.application.chats import ChatService
from ms_teams_cli.domain.chat_classifier import classify_chat
from ms_teams_cli.domain.chat_display import resolve_display_name
from ms_teams_cli.domain.models import Chat, ChatType

if TYPE_CHECKING:
    import pytest

    from ms_teams_cli.infrastructure.chat_client import ChatServiceClient


app = cli_module.app
runner = CliRunner()


class FakeChatClient:
    def __init__(
        self,
        payload: dict[str, object],
        service_url: str = "https://chat.example.test",
    ) -> None:
        self._payload: dict[str, object] = payload
        self._service_url: str = service_url
        self.called_urls: list[str] = []
        self.responses: dict[str, dict[str, object]] = {}

    def get_service_url(self) -> str:
        return self._service_url

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        return self.responses.get(url, self._payload)


class FakeChatTokenCache:
    def __init__(self) -> None:
        pass


class FakeChatTokenProvider:
    def __init__(self, cache: FakeChatTokenCache | None = None) -> None:
        self.cache: FakeChatTokenCache | None = cache

    def get_token(self) -> tuple[str, str]:
        return "token123", "https://chat.example.test"


class FakeChatClientFactory:
    def __init__(self, token_provider: FakeChatTokenProvider) -> None:
        self.token_provider: FakeChatTokenProvider = token_provider


class FakeChatService:
    chats: list[Chat] = []
    list_calls: list[dict[str, object]] = []

    def __init__(self, chat_client: FakeChatClientFactory) -> None:
        self.chat_client: FakeChatClientFactory = chat_client

    def list_chats(self, top: int = 50, chat_type: ChatType | None = None) -> list[Chat]:
        self.list_calls.append({"top": top, "chat_type": chat_type})
        return self.chats


def test_classify_chat_meeting() -> None:
    assert classify_chat("19:abc:meeting_xyz@thread.v2") == ChatType.MEETING


def test_classify_chat_group_thread_v2() -> None:
    assert classify_chat("19:abc@thread.v2") == ChatType.GROUP


def test_classify_chat_group_thread_tacv2() -> None:
    assert classify_chat("19:abc@thread.tacv2") == ChatType.GROUP


def test_classify_chat_one_to_one_unq() -> None:
    assert classify_chat("19:abc_def@unq.gbl.spaces") == ChatType.ONE_TO_ONE


def test_classify_chat_one_to_one_orgid() -> None:
    assert classify_chat("8:orgid:abc") == ChatType.ONE_TO_ONE


def test_classify_chat_other() -> None:
    assert classify_chat("19:abc@thread.skype") == ChatType.OTHER


def test_list_chats_returns_all_types() -> None:
    client = FakeChatClient(
        {
            "conversations": [
                {"id": "19:chat@thread.v2", "threadProperties": {"topic": "Group Chat"}},
                {
                    "id": "19:person@unq.gbl.spaces",
                    "lastMessage": {"imdisplayname": "Alice", "content": "<p>Hello</p>"},
                },
                {
                    "id": "19:meeting_123@thread.v2",
                    "threadProperties": {"topic": "Daily Standup"},
                },
            ]
        }
    )

    chats = ChatService(chat_client=cast("ChatServiceClient", cast("object", client))).list_chats()

    assert len(chats) == 3
    assert [chat.chat_type for chat in chats] == [
        ChatType.GROUP,
        ChatType.ONE_TO_ONE,
        ChatType.MEETING,
    ]


def test_list_chats_filters_by_type() -> None:
    client = FakeChatClient(
        {
            "conversations": [
                {"id": "19:g1@thread.v2", "threadProperties": {"topic": "Group 1"}},
                {"id": "19:g2@thread.tacv2", "threadProperties": {"topic": "Group 2"}},
                {"id": "19:p1@unq.gbl.spaces", "lastMessage": {"imdisplayname": "Alice"}},
                {"id": "8:orgid:bob", "lastMessage": {"imdisplayname": "Bob"}},
                {"id": "19:meeting_55@thread.v2", "threadProperties": {"topic": "Sync"}},
            ]
        }
    )

    chats = ChatService(chat_client=cast("ChatServiceClient", cast("object", client))).list_chats(
        chat_type=ChatType.GROUP
    )

    assert len(chats) == 2
    assert all(chat.chat_type == ChatType.GROUP for chat in chats)


def test_list_chats_empty() -> None:
    client = FakeChatClient({"conversations": []})

    chats = ChatService(chat_client=cast("ChatServiceClient", cast("object", client))).list_chats()

    assert chats == []


def test_list_chats_uses_requested_page_size() -> None:
    client = FakeChatClient({"conversations": []}, service_url="https://chat.example.test")

    _ = ChatService(
        chat_client=cast("ChatServiceClient", cast("object", client))
    ).list_chats(top=25)

    assert client.called_urls == [
        "https://chat.example.test/v1/users/ME/conversations?view=mychats&pageSize=25"
    ]


def test_list_chats_strips_html_preview() -> None:
    client = FakeChatClient(
        {
            "conversations": [
                {
                    "id": "19:p1@unq.gbl.spaces",
                    "lastMessage": {
                        "imdisplayname": "Alice",
                        "content": "<p>Hello&nbsp;<b>world</b></p>",
                        "composetime": "2026-03-28T10:30:00.000Z",
                    },
                }
            ]
        }
    )

    chats = ChatService(chat_client=cast("ChatServiceClient", cast("object", client))).list_chats()

    assert chats[0].last_message_preview == "Hello world"
    assert chats[0].last_message_time == "2026-03-28T10:30:00.000Z"


def test_resolve_display_name_uses_topic() -> None:
    client = FakeChatClient({})

    result = resolve_display_name(
        {"id": "19:g1@thread.v2", "threadProperties": {"topic": "Architecture"}},
        client,
        "https://chat.example.test",
    )

    assert result == "Architecture"


def test_resolve_display_name_uses_sender() -> None:
    client = FakeChatClient({})

    result = resolve_display_name(
        {
            "id": "19:p1@unq.gbl.spaces",
            "lastMessage": {"imdisplayname": "Alice", "fromDisplayNameInToken": "Bob"},
        },
        client,
        "https://chat.example.test",
    )

    assert result == "Chat with Alice"


def test_resolve_display_name_falls_back_to_other_person_lookup() -> None:
    conv_id = "19:p1@unq.gbl.spaces"
    client = FakeChatClient({})
    client.responses[
        f"https://chat.example.test/v1/users/ME/conversations/{conv_id}/messages?pageSize=10"
    ] = {"messages": [{"imdisplayname": "Me"}, {"imdisplayname": "Teammate"}]}

    result = resolve_display_name(
        {
            "id": conv_id,
            "lastMessage": {"imdisplayname": "Me", "fromDisplayNameInToken": "Me"},
        },
        client,
        "https://chat.example.test",
    )

    assert result == "Chat with Teammate"


def test_resolve_display_name_falls_back_to_id() -> None:
    client = FakeChatClient({})

    result = resolve_display_name(
        {"id": "19:abcdefghijklmnopqrstuvwxyz0123456789@thread.skype"},
        client,
        "https://chat.example.test",
    )

    assert result == "19:abcdefghijklmnopqrstuvwxyz0123456789@t"[:40]


def test_chats_cli_help() -> None:
    result = runner.invoke(app, ["chats", "--help"])
    assert result.exit_code == 0


def test_chats_cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeChatService.chats = [
        Chat(
            id="19:g1@thread.v2",
            chat_type=ChatType.GROUP,
            display_name="Architecture",
            last_message_preview="Hello",
            last_message_time="2026-03-28T10:30:00.000Z",
        )
    ]
    FakeChatService.list_calls = []

    monkeypatch.setattr(token_cache_module, "ChatTokenCache", FakeChatTokenCache)
    monkeypatch.setattr(az_provider_module, "AzChatTokenProvider", FakeChatTokenProvider)
    monkeypatch.setattr(chat_client_module, "ChatServiceClient", FakeChatClientFactory)
    monkeypatch.setattr(chats_module, "ChatService", FakeChatService)

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        print(json.dumps([item.model_dump(by_alias=False) for item in cast("list[Chat]", data)]))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["chats", "--type", "group", "--top", "10", "--json"])

    assert result.exit_code == 0
    assert FakeChatService.list_calls == [{"top": 10, "chat_type": ChatType.GROUP}]
    assert captured == [FakeChatService.chats]


def test_chats_cli_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_cache_module, "ChatTokenCache", FakeChatTokenCache)
    monkeypatch.setattr(az_provider_module, "AzChatTokenProvider", FakeChatTokenProvider)
    monkeypatch.setattr(chat_client_module, "ChatServiceClient", FakeChatClientFactory)
    monkeypatch.setattr(chats_module, "ChatService", FakeChatService)

    result = runner.invoke(app, ["chats", "--type", "bogus"])

    assert result.exit_code == 1
    assert "Invalid chat type: bogus" in result.stderr
