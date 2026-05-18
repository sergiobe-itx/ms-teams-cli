"""Tests for chat application service, classifier, display, and CLI."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from typer.testing import CliRunner

import ms_teams_cli.presentation.cli as cli_module
import ms_teams_cli.presentation.dependencies as deps_module
import ms_teams_cli.presentation.formatters as formatters_module
from ms_teams_cli.domain.entities import Chat, ChatType
from ms_teams_cli.domain.services import classify_chat, is_unread, resolve_display_name
from ms_teams_cli.infrastructure.chat import ChatServiceRepository

if TYPE_CHECKING:
    import pytest

    from ms_teams_cli.infrastructure.chat import ChatServiceClient


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
        self.post_calls: list[tuple[str, dict[str, object]]] = []
        self.post_response: dict[str, object] = {}

    def get_service_url(self) -> str:
        return self._service_url

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        return self.responses.get(url, self._payload)

    def post(self, url: str, body: dict[str, object]) -> dict[str, object]:
        self.post_calls.append((url, body))
        return self.post_response


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

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    chats = repo.list_chats()

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

    repo = ChatServiceRepository(
        chat_client=cast("ChatServiceClient", cast("object", client))
    )
    chats = repo.list_chats(chat_type=ChatType.GROUP)

    assert len(chats) == 2
    assert all(chat.chat_type == ChatType.GROUP for chat in chats)


def test_list_chats_empty() -> None:
    client = FakeChatClient({"conversations": []})

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    chats = repo.list_chats()

    assert chats == []


def test_list_chats_uses_requested_page_size() -> None:
    client = FakeChatClient({"conversations": []}, service_url="https://chat.example.test")

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    _ = repo.list_chats(top=25)

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

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    chats = repo.list_chats()

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
    chats = [
        Chat(
            id="19:g1@thread.v2",
            chat_type=ChatType.GROUP,
            display_name="Architecture",
            last_message_preview="Hello",
            last_message_time="2026-03-28T10:30:00.000Z",
        )
    ]

    class _FakeUseCase:
        def execute(self, *args: object, **kwargs: object) -> list[Chat]:
            return chats

    monkeypatch.setattr(deps_module, "get_list_chats", lambda: _FakeUseCase())

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        print(json.dumps([item.model_dump(by_alias=False) for item in cast("list[Chat]", data)]))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["chats", "--type", "group", "--top", "10", "--json"])

    assert result.exit_code == 0
    assert captured == [chats]


def test_chats_cli_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(app, ["chats", "--type", "bogus"])

    assert result.exit_code == 1
    assert "Invalid chat type: bogus" in result.stderr


def test_is_unread_newer_id_than_horizon() -> None:
    conv: dict[str, object] = {
        "lastMessage": {"id": "200"},
        "properties": {"consumptionhorizon": "100;x;x"},
    }
    assert is_unread(conv) is True


def test_is_unread_older_id_than_horizon() -> None:
    conv: dict[str, object] = {
        "lastMessage": {"id": "100"},
        "properties": {"consumptionhorizon": "200;x;x"},
    }
    assert is_unread(conv) is False


def test_is_unread_no_horizon() -> None:
    conv: dict[str, object] = {
        "lastMessage": {"id": "500"},
        "properties": {},
    }
    assert is_unread(conv) is True


def test_is_unread_no_last_message() -> None:
    conv: dict[str, object] = {
        "properties": {"consumptionhorizon": "100;x;x"},
    }
    assert is_unread(conv) is False


def test_is_unread_unparseable_horizon() -> None:
    conv: dict[str, object] = {
        "lastMessage": {"id": "300"},
        "properties": {"consumptionhorizon": "not;numbers;here"},
    }
    assert is_unread(conv) is True


def test_list_unread_filters_unread() -> None:
    client = FakeChatClient(
        {
            "conversations": [
                {
                    "id": "19:a@thread.v2",
                    "threadProperties": {"topic": "Unread 1"},
                    "lastMessage": {"id": "200"},
                    "properties": {"consumptionhorizon": "100;x;x"},
                },
                {
                    "id": "19:b@thread.v2",
                    "threadProperties": {"topic": "Read"},
                    "lastMessage": {"id": "50"},
                    "properties": {"consumptionhorizon": "200;x;x"},
                },
                {
                    "id": "19:c@unq.gbl.spaces",
                    "lastMessage": {"id": "999", "imdisplayname": "Alice"},
                    "properties": {},
                },
            ]
        }
    )

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    chats = repo.list_unread()

    assert len(chats) == 2


def test_list_unread_filters_by_type() -> None:
    client = FakeChatClient(
        {
            "conversations": [
                {
                    "id": "19:g1@thread.v2",
                    "threadProperties": {"topic": "Group1"},
                    "lastMessage": {"id": "200"},
                    "properties": {"consumptionhorizon": "100;x;x"},
                },
                {
                    "id": "19:g2@thread.tacv2",
                    "threadProperties": {"topic": "Group2"},
                    "lastMessage": {"id": "200"},
                    "properties": {"consumptionhorizon": "100;x;x"},
                },
                {
                    "id": "19:p1@unq.gbl.spaces",
                    "lastMessage": {"id": "500", "imdisplayname": "Bob"},
                    "properties": {},
                },
                {
                    "id": "19:meeting_1@thread.v2",
                    "threadProperties": {"topic": "Standup"},
                    "lastMessage": {"id": "300"},
                    "properties": {"consumptionhorizon": "100;x;x"},
                },
            ]
        }
    )

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    chats = repo.list_unread(chat_type=ChatType.GROUP)

    assert len(chats) == 2
    assert all(chat.chat_type == ChatType.GROUP for chat in chats)


def test_get_messages_returns_chronological_order() -> None:
    client = FakeChatClient({})
    chat_id = "19:abc@thread.v2"
    client.responses[
        f"https://chat.example.test/v1/users/ME/conversations/{chat_id}/messages?pageSize=30"
    ] = {
        "messages": [
            {
                "id": "4", "composetime": "2026-01-04T00:00:00Z",
                "imdisplayname": "D", "content": "d", "messagetype": "Text",
            },
            {
                "id": "3", "composetime": "2026-01-03T00:00:00Z",
                "imdisplayname": "C", "content": "c", "messagetype": "Text",
            },
            {
                "id": "2", "composetime": "2026-01-02T00:00:00Z",
                "imdisplayname": "B", "content": "b", "messagetype": "RichText",
            },
            {
                "id": "1", "composetime": "2026-01-01T00:00:00Z",
                "imdisplayname": "A", "content": "a", "messagetype": "Text",
            },
        ]
    }

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    messages = repo.get_messages(chat_id=chat_id)

    assert [m.id for m in messages] == ["1", "2", "3", "4"]


def test_get_messages_filters_to_user_types() -> None:
    client = FakeChatClient({})
    chat_id = "19:abc@thread.v2"
    client.responses[
        f"https://chat.example.test/v1/users/ME/conversations/{chat_id}/messages?pageSize=30"
    ] = {
        "messages": [
            {"id": "1", "messagetype": "Text", "imdisplayname": "A", "content": "hi"},
            {"id": "2", "messagetype": "RichText", "imdisplayname": "B", "content": "hey"},
            {
                "id": "3", "messagetype": "RichText/Html",
                "imdisplayname": "C", "content": "<b>ok</b>",
            },
            {"id": "4", "messagetype": "ThreadActivity/AddMember", "content": ""},
            {"id": "5", "messagetype": "Text", "imdisplayname": "D", "content": "sup"},
            {"id": "6", "messagetype": "Control/Typing", "content": ""},
            {"id": "7", "messagetype": "Text", "imdisplayname": "E", "content": "yo"},
            {
                "id": "8", "messagetype": "RichText/Html",
                "imdisplayname": "F", "content": "<i>bye</i>",
            },
        ]
    }

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    messages = repo.get_messages(chat_id=chat_id)

    assert len(messages) == 6
    assert all(m.message_type in {"Text", "RichText", "RichText/Html"} for m in messages)


def test_chat_messages_cli_help() -> None:
    result = runner.invoke(app, ["chat-messages", "--help"])
    assert result.exit_code == 0


def test_unread_cli_help() -> None:
    result = runner.invoke(app, ["unread", "--help"])
    assert result.exit_code == 0


def test_send_message_posts_correct_body() -> None:
    client = FakeChatClient({"conversations": []})
    client.post_response = {"OriginalArrivalTime": "12345"}

    repo = ChatServiceRepository(
        chat_client=cast("ChatServiceClient", cast("object", client))
    )
    repo.send_message("19:abc@thread.v2", "Hello world")

    assert len(client.post_calls) == 1
    url, body = client.post_calls[0]
    assert url == "https://chat.example.test/v1/users/ME/conversations/19:abc@thread.v2/messages"
    assert body["content"] == "Hello world"
    assert body["messagetype"] == "Text"
    assert body["contenttype"] == "text"


def test_send_message_html_detection() -> None:
    client = FakeChatClient({"conversations": []})
    client.post_response = {"id": "1"}

    repo = ChatServiceRepository(
        chat_client=cast("ChatServiceClient", cast("object", client))
    )
    repo.send_message("19:abc@thread.v2", "<b>Bold</b> text")

    _, body = client.post_calls[0]
    assert body["messagetype"] == "RichText/Html"


def test_send_message_no_robot_emoji() -> None:
    client = FakeChatClient({"conversations": []})
    client.post_response = {"id": "1"}

    repo = ChatServiceRepository(
        chat_client=cast("ChatServiceClient", cast("object", client))
    )
    repo.send_message("19:abc@thread.v2", "Test message")

    _, body = client.post_calls[0]
    content = str(body["content"])
    assert not content.startswith("\U0001f916")
    assert content == "Test message"


def test_send_message_returns_original_arrival_time() -> None:
    client = FakeChatClient({"conversations": []})
    client.post_response = {"OriginalArrivalTime": "12345"}

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    result = repo.send_message("19:abc@thread.v2", "hi")

    assert result == "12345"


def test_send_message_falls_back_to_id() -> None:
    client = FakeChatClient({"conversations": []})
    client.post_response = {"id": "99"}

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    result = repo.send_message("19:abc@thread.v2", "hi")

    assert result == "99"


def test_resolve_chat_name_finds_match() -> None:
    client = FakeChatClient(
        {
            "conversations": [
                {"id": "19:target@thread.v2", "threadProperties": {"topic": "My Chat"}},
                {"id": "19:other@thread.v2", "threadProperties": {"topic": "Other"}},
            ]
        }
    )

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    result = repo.resolve_chat_name("19:target@thread.v2")

    assert result == "My Chat"


def test_resolve_chat_name_fallback_to_id() -> None:
    client = FakeChatClient({"conversations": []})

    repo = ChatServiceRepository(chat_client=cast("ChatServiceClient", cast("object", client)))

    result = repo.resolve_chat_name("19:nonexistent@thread.v2")

    assert result == "19:nonexistent@thread.v2"


def test_send_message_cli_help() -> None:
    result = runner.invoke(app, ["send-message", "--help"])
    assert result.exit_code == 0
