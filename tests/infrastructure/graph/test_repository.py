"""Tests for GraphChannelRepository adapter (HTTP-mocked)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.entities import Channel, ChannelMessage, Team
from ms_teams_cli.infrastructure.graph import GraphChannelRepository

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.graph import GraphClient


class FakeGraphClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload: dict[str, object] = payload
        self.called_urls: list[str] = []
        self.paginate_calls: list[tuple[str, int]] = []

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        return self._payload

    def paginate(
        self, url: str, max_pages: int = 1, stop_before: str | None = None
    ) -> list[dict[str, object]]:
        self.paginate_calls.append((url, max_pages))
        value = self._payload.get("value", [])
        if isinstance(value, list):
            return cast("list[dict[str, object]]", value)
        return []


def _now_iso(offset_minutes: int = 0) -> str:
    dt = datetime.now(UTC) + timedelta(minutes=offset_minutes)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_list_teams_returns_team_objects() -> None:
    client = FakeGraphClient(
        {
            "value": [
                {"id": "t1", "displayName": "Team A", "description": "desc"},
                {"id": "t2", "displayName": "Team B", "description": None},
            ]
        }
    )

    repo = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    teams = repo.list_teams()

    assert teams == [
        Team(id="t1", displayName="Team A", description="desc"),
        Team(id="t2", displayName="Team B", description=None),
    ]


def test_list_teams_empty() -> None:
    client = FakeGraphClient({"value": []})

    repo = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    teams = repo.list_teams()

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

    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    channels = service.list_channels("team-123")

    assert channels == [
        Channel(id="c1", displayName="General", description="main"),
        Channel(id="c2", displayName="Random", description=None),
    ]


def test_list_channels_empty() -> None:
    client = FakeGraphClient({"value": []})

    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    channels = service.list_channels("team-123")

    assert channels == []


def test_list_channels_uses_correct_url() -> None:
    client = FakeGraphClient({"value": []})

    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
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

    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    messages = list(service.get_messages("team-123", "channel-456"))

    assert len(messages) == 3
    assert all(isinstance(message, ChannelMessage) for message in messages)
    assert messages[0].id == "m1"
    assert messages[0].author.display_name == "Alice Johnson"
    assert messages[0].body.content == "<p>Hello</p>"


def test_get_messages_empty() -> None:
    client = FakeGraphClient({"value": []})

    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    messages = list(service.get_messages("team-123", "channel-456"))

    assert messages == []


def test_get_messages_url_construction_with_since() -> None:
    client = FakeGraphClient({"value": []})

    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
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


def test_get_thread_returns_parent_and_replies() -> None:
    parent_data = {
        "id": "m1",
        "messageType": "message",
        "createdDateTime": "2024-01-15T14:30:00Z",
        "replyCount": 2,
        "from": {"user": {"displayName": "Alice Johnson"}},
        "body": {"contentType": "html", "content": "<p>Original post</p>"},
    }
    replies_data: dict[str, object] = {
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
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    parent, replies = service.get_thread("team-123", "channel-456", "msg-789", top=50)

    assert isinstance(parent, ChannelMessage)
    assert parent.id == "m1"
    assert parent.author.display_name == "Alice Johnson"
    assert len(replies) == 2
    assert all(isinstance(r, ChannelMessage) for r in replies)
    assert replies[0].id == "r1"
    assert replies[1].id == "r2"


def test_get_thread_empty_replies() -> None:
    parent_data = {
        "id": "m1",
        "messageType": "message",
        "createdDateTime": "2024-01-15T14:30:00Z",
        "replyCount": 0,
        "from": {"user": {"displayName": "Alice Johnson"}},
        "body": {"contentType": "html", "content": "<p>Original post</p>"},
    }
    replies_data: dict[str, object] = {"value": []}

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
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    parent, replies = service.get_thread("team-123", "channel-456", "msg-789")

    assert isinstance(parent, ChannelMessage)
    assert parent.id == "m1"
    assert replies == []


def test_find_unanswered_filters_all_five_conditions() -> None:
    now = _now_iso(0)
    old = "2020-01-01T00:00:00Z"
    messages: list[dict[str, object]] = [
        {"id": "1", "messageType": "message", "createdDateTime": now, "replyCount": 2,
         "from": {"user": {"displayName": "A"}}, "body": {"content": "x"}},
        {"id": "2", "messageType": "message", "createdDateTime": now, "replyCount": 1,
         "from": {"user": {"displayName": "B"}}, "body": {"content": "x"}},
        {"id": "3", "messageType": "systemEventMessage", "createdDateTime": now, "replyCount": 0,
         "from": {"user": {"displayName": "C"}}, "body": {"content": "x"}},
        {"id": "4", "messageType": "unknownFutureValue", "createdDateTime": now, "replyCount": 0,
         "from": {"user": {"displayName": "D"}}, "body": {"content": "x"}},
        {"id": "5", "messageType": "message", "createdDateTime": now, "replyCount": 0,
         "deletedDateTime": "2024-01-01T00:00:00Z",
         "from": {"user": {"displayName": "E"}}, "body": {"content": "x"}},
        {"id": "6", "messageType": "message", "createdDateTime": now, "replyCount": 0,
         "replyToId": "parent-id",
         "from": {"user": {"displayName": "F"}}, "body": {"content": "x"}},
        {"id": "7", "messageType": "message", "createdDateTime": old, "replyCount": 0,
         "from": {"user": {"displayName": "G"}}, "body": {"content": "x"}},
        {"id": "8", "messageType": "message", "createdDateTime": old, "replyCount": 0,
         "from": {"user": {"displayName": "H"}}, "body": {"content": "x"}},
        {"id": "9", "messageType": "message", "createdDateTime": now, "replyCount": 0,
         "from": {"user": {"displayName": "I"}}, "body": {"content": "x"}},
        {"id": "10", "messageType": "message", "createdDateTime": now,
         "from": {"user": {"displayName": "J"}}, "body": {"content": "x"}},
    ]

    client = FakeGraphClient({"value": messages})
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    result = service.find_unanswered("t1", "c1", minutes=120)

    assert len(result) == 2
    assert {m.id for m in result} == {"9", "10"}


def test_find_unanswered_empty() -> None:
    client = FakeGraphClient({"value": []})
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    result = service.find_unanswered("t1", "c1")

    assert result == []


def test_find_unanswered_uses_correct_url() -> None:
    client = FakeGraphClient({"value": []})
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    _ = service.find_unanswered("team-abc", "channel-xyz", minutes=60)

    assert len(client.called_urls) == 1
    assert "team-abc" in client.called_urls[0]
    assert "channel-xyz" in client.called_urls[0]
    assert "messages" in client.called_urls[0]


def test_scan_activity_validates_date_format() -> None:
    import pytest as _pytest

    client = FakeGraphClient({"value": []})
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))

    with _pytest.raises(ValueError, match="date must be YYYY-MM-DD"):
        service.scan_activity("t1", "not-a-date")

    with _pytest.raises(ValueError, match="date must be YYYY-MM-DD"):
        service.scan_activity("t1", "2024/01/15")

    with _pytest.raises(ValueError, match="date must be YYYY-MM-DD"):
        service.scan_activity("t1", "01-15-2024")


def test_scan_activity_stop_before_calculation() -> None:
    target = "2024-06-15"
    expected_stop = (
        datetime.strptime(target, "%Y-%m-%d") - timedelta(days=3)
    ).strftime("%Y-%m-%d")
    assert expected_stop == "2024-06-12"

    class StopBeforeCapture:
        def __init__(self) -> None:
            self.called_urls: list[str] = []
            self.paginate_stop_before: list[str | None] = []

        def get(self, url: str) -> dict[str, object]:
            self.called_urls.append(url)
            return {"value": []}

        def paginate(
            self, url: str, max_pages: int = 1, stop_before: str | None = None
        ) -> list[dict[str, object]]:
            self.paginate_stop_before.append(stop_before)
            return []

    client = StopBeforeCapture()
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))

    client.get = lambda url: {"value": [{"id": "c1", "displayName": "General"}]}  # type: ignore[assignment]
    result = service.scan_activity("t1", target, pages=2)

    assert client.paginate_stop_before == ["2024-06-12"]
    assert result.date == target
    assert result.channels == []


def test_scan_activity_aggregates_correctly() -> None:
    target = "2024-06-15"

    class ScanFakeClient:
        def __init__(self) -> None:
            self.called_urls: list[str] = []

        def get(self, url: str) -> dict[str, object]:
            self.called_urls.append(url)
            if "channels?" in url:
                return {"value": [
                    {"id": "c1", "displayName": "Channel 1"},
                    {"id": "c2", "displayName": "Channel 2"},
                ]}
            if "/replies?" in url:
                if "c1" in url:
                    return {"value": []}
                return {"value": [
                    {"id": "r1", "messageType": "message",
                     "createdDateTime": "2024-06-15T10:00:00Z", "replyCount": 0,
                     "from": {"user": {"displayName": "Reply Author"}},
                     "body": {"content": "reply"}},
                ]}
            return {"value": []}

        def paginate(
            self, url: str, max_pages: int = 1, stop_before: str | None = None
        ) -> list[dict[str, object]]:
            if "c1" in url:
                return [
                    {"id": "m1", "messageType": "message",
                     "createdDateTime": "2024-06-15T09:00:00Z", "replyCount": 0,
                     "from": {"user": {"displayName": "Author 1"}},
                     "body": {"content": "post"}},
                ]
            if "c2" in url:
                return [
                    {"id": "m2", "messageType": "message",
                     "createdDateTime": "2024-06-14T09:00:00Z", "replyCount": 1,
                     "from": {"user": {"displayName": "Author 2"}},
                     "body": {"content": "older post"}},
                ]
            return []

    client = ScanFakeClient()
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    result = service.scan_activity("t1", target, pages=2)

    assert len(result.channels) == 2
    assert result.channels[0].channel_name == "Channel 1"
    assert result.channels[0].threads[0].root_created_on_date is True
    assert result.channels[1].channel_name == "Channel 2"
    assert result.channels[1].threads[0].root_created_on_date is False
    assert len(result.channels[1].threads[0].replies_on_date) == 1


def test_scan_activity_excludes_channels_with_no_activity() -> None:
    target = "2024-06-15"

    class NoActivityClient:
        def get(self, url: str) -> dict[str, object]:
            if "channels?" in url:
                return {"value": [
                    {"id": "c1", "displayName": "Empty Channel"},
                ]}
            if "/replies?" in url:
                return {"value": []}
            return {"value": []}

        def paginate(
            self, url: str, max_pages: int = 1, stop_before: str | None = None
        ) -> list[dict[str, object]]:
            return [
                {"id": "m1", "messageType": "message",
                 "createdDateTime": "2024-06-10T09:00:00Z", "replyCount": 0,
                 "from": {"user": {"displayName": "X"}},
                 "body": {"content": "old"}},
            ]

    client = NoActivityClient()
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    result = service.scan_activity("t1", target, pages=2)

    assert result.channels == []


def test_scan_activity_thread_includes_if_root_on_date() -> None:
    target = "2024-06-15"

    class RootOnDateClient:
        def get(self, url: str) -> dict[str, object]:
            if "channels?" in url:
                return {"value": [{"id": "c1", "displayName": "Ch1"}]}
            if "/replies?" in url:
                return {"value": []}
            return {"value": []}

        def paginate(
            self, url: str, max_pages: int = 1, stop_before: str | None = None
        ) -> list[dict[str, object]]:
            return [
                {"id": "m1", "messageType": "message",
                 "createdDateTime": "2024-06-15T12:00:00Z", "replyCount": 0,
                 "from": {"user": {"displayName": "Author"}},
                 "body": {"content": "on day"}},
            ]

    client = RootOnDateClient()
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    result = service.scan_activity("t1", target, pages=2)

    assert len(result.channels) == 1
    thread = result.channels[0].threads[0]
    assert thread.root_created_on_date is True
    assert thread.replies_on_date == []


def test_scan_activity_thread_includes_if_reply_on_date() -> None:
    target = "2024-06-15"

    class ReplyOnDateClient:
        def get(self, url: str) -> dict[str, object]:
            if "channels?" in url:
                return {"value": [{"id": "c1", "displayName": "Ch1"}]}
            if "/replies?" in url:
                return {"value": [
                    {"id": "r1", "messageType": "message",
                     "createdDateTime": "2024-06-15T14:00:00Z", "replyCount": 0,
                     "from": {"user": {"displayName": "Replier"}},
                     "body": {"content": "reply text"}},
                ]}
            return {"value": []}

        def paginate(
            self, url: str, max_pages: int = 1, stop_before: str | None = None
        ) -> list[dict[str, object]]:
            return [
                {"id": "m1", "messageType": "message",
                 "createdDateTime": "2024-06-13T09:00:00Z", "replyCount": 1,
                 "from": {"user": {"displayName": "Root Author"}},
                 "body": {"content": "older root"}},
            ]

    client = ReplyOnDateClient()
    service = GraphChannelRepository(graph_client=cast("GraphClient", cast("object", client)))
    result = service.scan_activity("t1", target, pages=2)

    assert len(result.channels) == 1
    thread = result.channels[0].threads[0]
    assert thread.root_created_on_date is False
    assert len(thread.replies_on_date) == 1
    assert thread.replies_on_date[0].id == "r1"
