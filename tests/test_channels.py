"""Tests for channel application service and teams CLI."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from typer.testing import CliRunner

import ms_teams_cli.application.channels as channels_module
import ms_teams_cli.infrastructure.az_provider as az_provider_module
import ms_teams_cli.infrastructure.graph_client as graph_client_module
import ms_teams_cli.infrastructure.token_cache as token_cache_module
import ms_teams_cli.presentation.cli as cli_module
import ms_teams_cli.presentation.formatters as formatters_module
from ms_teams_cli.application.channels import ChannelService
from ms_teams_cli.domain.models import Channel, ChannelMessage, MessageAuthor, MessageBody, Team

if TYPE_CHECKING:
    import pytest

    from ms_teams_cli.infrastructure.graph_client import GraphClient


app = cli_module.app
runner = CliRunner()


class FakeGraphClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload: dict[str, object] = payload
        self.called_urls: list[str] = []
        self.paginate_calls: list[tuple[str, int]] = []

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        return self._payload

    def paginate(self, url: str, max_pages: int = 1) -> list[dict[str, object]]:
        self.paginate_calls.append((url, max_pages))
        value = self._payload.get("value", [])
        if isinstance(value, list):
            return cast("list[dict[str, object]]", value)
        return []


class FakeTokenCache:
    def __init__(self) -> None:
        pass


class FakeTokenProvider:
    def __init__(self, cache: FakeTokenCache | None = None) -> None:
        self.cache: FakeTokenCache | None = cache


class FakeGraphClientFactory:
    def __init__(self, token_provider: FakeTokenProvider) -> None:
        self.token_provider: FakeTokenProvider = token_provider


class FakeChannelService:
    teams: list[Team] = []
    channels: list[Channel] = []
    messages: list[ChannelMessage] = []
    get_messages_calls: list[dict[str, object]] = []
    thread_result: tuple[ChannelMessage, list[ChannelMessage]] | None = None
    get_thread_calls: list[dict[str, object]] = []

    def __init__(self, graph_client: FakeGraphClientFactory) -> None:
        self.graph_client: FakeGraphClientFactory = graph_client

    def list_teams(self) -> list[Team]:
        return self.teams

    def list_channels(self, _team_id: str) -> list[Channel]:
        return self.channels

    def get_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 20,
        pages: int = 1,
        since: str | None = None,
    ) -> list[ChannelMessage]:
        self.get_messages_calls.append(
            {
                "team_id": team_id,
                "channel_id": channel_id,
                "top": top,
                "pages": pages,
                "since": since,
            }
        )
        return self.messages

    def get_thread(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        top: int = 50,
    ) -> tuple[ChannelMessage, list[ChannelMessage]]:
        self.get_thread_calls.append(
            {
                "team_id": team_id,
                "channel_id": channel_id,
                "message_id": message_id,
                "top": top,
            }
        )
        if self.thread_result:
            return self.thread_result
        return (
            ChannelMessage(
                id="m0",
                createdDateTime="2024-01-15T14:30:00Z",
                author=MessageAuthor(displayName="Alice"),
                body=MessageBody(content="<p>Parent</p>", contentType="html"),
                replyCount=0,
                messageType="message",
                replyToId=None,
            ),
            [],
        )


def test_list_teams_returns_team_objects() -> None:
    client = FakeGraphClient(
        {
            "value": [
                {"id": "t1", "displayName": "Team A", "description": "desc"},
                {"id": "t2", "displayName": "Team B", "description": None},
            ]
        }
    )

    teams = ChannelService(graph_client=cast("GraphClient", cast("object", client))).list_teams()

    assert teams == [
        Team(id="t1", displayName="Team A", description="desc"),
        Team(id="t2", displayName="Team B", description=None),
    ]


def test_list_teams_empty() -> None:
    client = FakeGraphClient({"value": []})

    teams = ChannelService(graph_client=cast("GraphClient", cast("object", client))).list_teams()

    assert teams == []


def test_list_channels_returns_channel_objects() -> None:
    client = FakeGraphClient(
        {
            "value": [
                {"id": "c1", "displayName": "General", "description": "main"},
                {"id": "c2", "displayName": "Random", "description": None},
            ]
        }
    )

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    channels = service.list_channels("team-123")

    assert channels == [
        Channel(id="c1", displayName="General", description="main"),
        Channel(id="c2", displayName="Random", description=None),
    ]


def test_list_channels_empty() -> None:
    client = FakeGraphClient({"value": []})

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    channels = service.list_channels("team-123")

    assert channels == []


def test_list_channels_uses_correct_url() -> None:
    client = FakeGraphClient({"value": []})

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    _ = service.list_channels("team-id-123")

    assert len(client.called_urls) == 1
    assert "team-id-123" in client.called_urls[0]
    assert "channels" in client.called_urls[0]


def test_get_messages_returns_channel_message_objects() -> None:
    client = FakeGraphClient(
        {
            "value": [
                {
                    "id": "m1",
                    "messageType": "message",
                    "createdDateTime": "2024-01-15T14:30:00Z",
                    "replyCount": 3,
                    "from": {"user": {"displayName": "Alice Johnson"}},
                    "body": {"contentType": "html", "content": "<p>Hello</p>"},
                },
                {
                    "id": "m2",
                    "messageType": "message",
                    "createdDateTime": "2024-01-15T14:31:00Z",
                    "replyCount": 0,
                    "from": {"user": {"displayName": "Bob Smith"}},
                    "body": {"contentType": "html", "content": "<p>Hi</p>"},
                },
                {
                    "id": "m3",
                    "messageType": "message",
                    "createdDateTime": "2024-01-15T14:32:00Z",
                    "replyCount": 1,
                    "from": {"user": {"displayName": "Carol Jones"}},
                    "body": {"contentType": "html", "content": "<p>Hey</p>"},
                },
            ]
        }
    )

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    messages = list(service.get_messages("team-123", "channel-456"))

    assert len(messages) == 3
    assert all(isinstance(message, ChannelMessage) for message in messages)
    assert messages[0].id == "m1"
    assert messages[0].author.display_name == "Alice Johnson"
    assert messages[0].body.content == "<p>Hello</p>"


def test_get_messages_empty() -> None:
    client = FakeGraphClient({"value": []})

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    messages = list(service.get_messages("team-123", "channel-456"))

    assert messages == []


def test_get_messages_url_construction_with_since() -> None:
    client = FakeGraphClient({"value": []})

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    _ = list(
        service.get_messages(
            "team-123",
            "channel-456",
            top=20,
            pages=2,
            since="2024-01-01T00:00:00Z",
        )
    )

    assert client.paginate_calls == [
        (
            "https://graph.microsoft.com/beta/teams/team-123/channels/channel-456/messages"
            + "?$top=20&$filter=createdDateTime%20ge%202024-01-01T00:00:00Z",
            2,
        )
    ]


def test_teams_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    teams = [
        Team(id="t1", displayName="Team A", description="desc"),
        Team(id="t2", displayName="Team B", description=None),
    ]
    FakeChannelService.teams = teams

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[list[Team]] = []

    def fake_formatter(items: list[Team]) -> None:
        captured.append(items)
        for item in items:
            print(item.display_name)
        print(f"{len(items)} teams.")

    monkeypatch.setattr(formatters_module, "format_teams_table", fake_formatter)

    result = runner.invoke(app, ["teams"])

    assert result.exit_code == 0
    assert captured == [teams]
    assert "Team A" in result.stdout
    assert "Team B" in result.stdout
    assert "2 teams." in result.stdout


def test_teams_cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    teams = [Team(id="t1", displayName="Team A", description="desc")]
    FakeChannelService.teams = teams

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        item = cast("list[Team]", data)[0]
        print(json.dumps(item.model_dump(by_alias=False)))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["teams", "--json"])

    assert result.exit_code == 0
    assert captured == [teams]
    assert json.loads(result.stdout) == {
        "id": "t1",
        "display_name": "Team A",
        "description": "desc",
    }


def test_channels_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    channels = [
        Channel(id="c1", displayName="General", description="main"),
        Channel(id="c2", displayName="Random", description=None),
    ]
    FakeChannelService.channels = channels

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[list[Channel]] = []

    def fake_formatter(items: list[Channel]) -> None:
        captured.append(items)
        for item in items:
            print(item.display_name)
        print(f"{len(items)} channels.")

    monkeypatch.setattr(formatters_module, "format_channels_table", fake_formatter)

    result = runner.invoke(app, ["channels", "--team", "t1"])

    assert result.exit_code == 0
    assert captured == [channels]
    assert "General" in result.stdout
    assert "Random" in result.stdout
    assert "2 channels." in result.stdout


def test_channels_cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    channels = [Channel(id="c1", displayName="General", description="main")]
    FakeChannelService.channels = channels

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        item = cast("list[Channel]", data)[0]
        print(json.dumps(item.model_dump(by_alias=False)))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["channels", "--team", "t1", "--json"])

    assert result.exit_code == 0
    assert captured == [channels]
    assert json.loads(result.stdout) == {
        "id": "c1",
        "display_name": "General",
        "description": "main",
    }


def test_messages_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = [
        ChannelMessage(
            id="m1",
            createdDateTime="2024-01-15T14:30:00Z",
            author=MessageAuthor(displayName="Alice Johnson"),
            body=MessageBody(content="<p>Hello</p>", contentType="html"),
            replyCount=3,
            messageType="message",
            replyToId=None,
        ),
        ChannelMessage(
            id="m2",
            createdDateTime="2024-01-15T14:31:00Z",
            author=MessageAuthor(displayName="Bob Smith"),
            body=MessageBody(content="<p>Hi</p>", contentType="html"),
            replyCount=0,
            messageType="message",
            replyToId=None,
        ),
    ]
    FakeChannelService.messages = messages
    FakeChannelService.get_messages_calls = []

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[list[ChannelMessage]] = []

    def fake_formatter(items: list[ChannelMessage]) -> None:
        captured.append(items)
        for item in items:
            print(item.author.display_name)
        print(f"{len(items)} messages.")

    monkeypatch.setattr(formatters_module, "format_messages_table", fake_formatter)

    result = runner.invoke(app, ["messages", "--team", "t1", "--channel", "c1"])

    assert result.exit_code == 0
    assert captured == [messages]
    assert FakeChannelService.get_messages_calls == [
        {
            "team_id": "t1",
            "channel_id": "c1",
            "top": 20,
            "pages": 1,
            "since": None,
        }
    ]
    assert "Alice Johnson" in result.stdout
    assert "Bob Smith" in result.stdout
    assert "2 messages." in result.stdout


def test_get_thread_returns_parent_and_replies() -> None:
    """Test that get_thread returns parent message and list of replies."""
    parent_data = {
        "id": "m1",
        "messageType": "message",
        "createdDateTime": "2024-01-15T14:30:00Z",
        "replyCount": 2,
        "from": {"user": {"displayName": "Alice Johnson"}},
        "body": {"contentType": "html", "content": "<p>Original post</p>"},
    }
    replies_data = {
        "value": [
            {
                "id": "r1",
                "messageType": "message",
                "createdDateTime": "2024-01-15T14:31:00Z",
                "replyCount": 0,
                "from": {"user": {"displayName": "Bob Smith"}},
                "body": {"contentType": "html", "content": "<p>Reply 1</p>"},
            },
            {
                "id": "r2",
                "messageType": "message",
                "createdDateTime": "2024-01-15T14:32:00Z",
                "replyCount": 0,
                "from": {"user": {"displayName": "Carol Jones"}},
                "body": {"contentType": "html", "content": "<p>Reply 2</p>"},
            },
        ]
    }

    class MultiResponseFakeClient:
        def __init__(self) -> None:
            self.called_urls: list[str] = []
            self.call_count = 0

        def get(self, url: str) -> dict[str, object]:
            self.called_urls.append(url)
            self.call_count += 1
            if "replies" in url:
                return replies_data
            return parent_data

        def paginate(self, url: str, max_pages: int = 1) -> list[dict[str, object]]:
            return []

    client = MultiResponseFakeClient()
    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    parent, replies = service.get_thread("team-123", "channel-456", "msg-789", top=50)

    assert isinstance(parent, ChannelMessage)
    assert parent.id == "m1"
    assert parent.author.display_name == "Alice Johnson"
    assert len(replies) == 2
    assert all(isinstance(r, ChannelMessage) for r in replies)
    assert replies[0].id == "r1"
    assert replies[1].id == "r2"


def test_get_thread_empty_replies() -> None:
    """Test that get_thread handles empty replies correctly."""
    parent_data = {
        "id": "m1",
        "messageType": "message",
        "createdDateTime": "2024-01-15T14:30:00Z",
        "replyCount": 0,
        "from": {"user": {"displayName": "Alice Johnson"}},
        "body": {"contentType": "html", "content": "<p>Original post</p>"},
    }
    replies_data = {"value": []}

    class MultiResponseFakeClient:
        def __init__(self) -> None:
            self.called_urls: list[str] = []

        def get(self, url: str) -> dict[str, object]:
            self.called_urls.append(url)
            if "replies" in url:
                return replies_data
            return parent_data

        def paginate(self, url: str, max_pages: int = 1) -> list[dict[str, object]]:
            return []

    client = MultiResponseFakeClient()
    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    parent, replies = service.get_thread("team-123", "channel-456", "msg-789")

    assert isinstance(parent, ChannelMessage)
    assert parent.id == "m1"
    assert replies == []


def test_replies_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that replies CLI command works end-to-end."""
    parent = ChannelMessage(
        id="m1",
        createdDateTime="2024-01-15T14:30:00Z",
        author=MessageAuthor(displayName="Alice Johnson"),
        body=MessageBody(content="<p>Original post</p>", contentType="html"),
        replyCount=1,
        messageType="message",
        replyToId=None,
    )
    reply = ChannelMessage(
        id="r1",
        createdDateTime="2024-01-15T14:31:00Z",
        author=MessageAuthor(displayName="Bob Smith"),
        body=MessageBody(content="<p>Reply</p>", contentType="html"),
        replyCount=0,
        messageType="message",
        replyToId="m1",
    )
    FakeChannelService.thread_result = (parent, [reply])
    FakeChannelService.get_thread_calls = []

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured_parent: list[ChannelMessage] = []
    captured_replies: list[list[ChannelMessage]] = []

    def fake_formatter(p: ChannelMessage, r: list[ChannelMessage]) -> None:
        captured_parent.append(p)
        captured_replies.append(r)
        print(f"From : {p.author.display_name}")
        print(f"Replies ({len(r)} total)")
        for reply_msg in r:
            print(f"  {reply_msg.author.display_name}")

    monkeypatch.setattr(formatters_module, "format_thread", fake_formatter)

    result = runner.invoke(app, ["replies", "--team", "t1", "--channel", "c1", "--thread", "m1"])

    assert result.exit_code == 0
    assert captured_parent == [parent]
    assert captured_replies == [[reply]]
    assert FakeChannelService.get_thread_calls == [
        {
            "team_id": "t1",
            "channel_id": "c1",
            "message_id": "m1",
            "top": 50,
        }
    ]
    assert "Alice Johnson" in result.stdout
    assert "Bob Smith" in result.stdout

