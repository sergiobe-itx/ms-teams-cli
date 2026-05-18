"""Tests for GraphCalendarRepository adapter."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ms_teams_cli.infrastructure.graph import GraphCalendarRepository

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.graph.client import GraphClient


class FakeGraphClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload: dict[str, object] = payload
        self.called_urls: list[str] = []

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        return self._payload


class MultiPageFakeClient:
    def __init__(self, page1: dict[str, object], page2: dict[str, object]) -> None:
        self._calls: int = 0
        self._page1 = page1
        self._page2 = page2
        self.called_urls: list[str] = []

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        self._calls += 1
        return self._page1 if self._calls == 1 else self._page2


_STANDUP = {
    "id": "ev1",
    "subject": "Standup",
    "isAllDay": False,
    "isCancelled": False,
    "start": {"dateTime": "2026-05-18T09:00:00.0000000", "timeZone": "UTC"},
    "end": {"dateTime": "2026-05-18T09:30:00.0000000", "timeZone": "UTC"},
    "organizer": {"emailAddress": {"name": "Alice Smith", "address": "alice@example.com"}},
}

_RETRO = {
    "id": "ev2",
    "subject": "Retro",
    "isAllDay": False,
    "isCancelled": False,
    "start": {"dateTime": "2026-05-18T14:00:00.0000000", "timeZone": "Europe/Madrid"},
    "end": {"dateTime": "2026-05-18T15:00:00.0000000", "timeZone": "Europe/Madrid"},
    "organizer": {"emailAddress": {"name": "Bob Jones", "address": "bob@example.com"}},
}


def test_list_events_basic() -> None:
    client = FakeGraphClient({"value": [_STANDUP, _RETRO]})
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    events = repo.list_events("2026-05-18", "2026-05-18")

    assert len(events) == 2
    assert events[0].id == "ev1"
    assert events[0].subject == "Standup"
    assert events[0].organizer_name == "Alice Smith"
    assert events[0].start_timezone == "UTC"
    assert events[1].id == "ev2"
    assert events[1].subject == "Retro"
    assert events[1].start_timezone == "Europe/Madrid"


def test_list_events_pagination() -> None:
    page1: dict[str, object] = {
        "value": [_STANDUP],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/calendarView?$skip=1",
    }
    page2: dict[str, object] = {
        "value": [_RETRO],
    }
    client = MultiPageFakeClient(page1, page2)
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    events = repo.list_events("2026-05-18", "2026-05-18")

    assert len(events) == 2
    assert len(client.called_urls) == 2
    assert events[0].subject == "Standup"
    assert events[1].subject == "Retro"


def test_list_events_skips_cancelled() -> None:
    cancelled = {
        "id": "ev3",
        "subject": "Cancelled Meeting",
        "isAllDay": False,
        "isCancelled": True,
        "start": {"dateTime": "2026-05-18T10:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-05-18T11:00:00.0000000", "timeZone": "UTC"},
        "organizer": {"emailAddress": {"name": "Carol", "address": "carol@example.com"}},
    }
    client = FakeGraphClient({"value": [_STANDUP, cancelled]})
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    events = repo.list_events("2026-05-18", "2026-05-18")

    assert len(events) == 1
    assert events[0].id == "ev1"


def test_list_events_empty() -> None:
    client = FakeGraphClient({"value": []})
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    events = repo.list_events("2026-05-18", "2026-05-18")

    assert events == []


def test_list_events_url_contains_dates() -> None:
    client = FakeGraphClient({"value": []})
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    repo.list_events("2026-05-18", "2026-05-20")

    assert len(client.called_urls) == 1
    assert "2026-05-18" in client.called_urls[0]
    assert "2026-05-20" in client.called_urls[0]
    assert "startDateTime" in client.called_urls[0]
    assert "endDateTime" in client.called_urls[0]


def test_list_events_all_day() -> None:
    all_day = {
        "id": "ev4",
        "subject": "Holiday",
        "isAllDay": True,
        "isCancelled": False,
        "start": {"dateTime": "2026-05-18T00:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-05-19T00:00:00.0000000", "timeZone": "UTC"},
        "organizer": {"emailAddress": {"name": "HR", "address": "hr@example.com"}},
    }
    client = FakeGraphClient({"value": [all_day]})
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    events = repo.list_events("2026-05-18", "2026-05-18")

    assert len(events) == 1
    assert events[0].is_all_day is True
    assert events[0].subject == "Holiday"


def test_list_events_no_subject() -> None:
    no_subject = {
        "id": "ev5",
        "subject": None,
        "isAllDay": False,
        "isCancelled": False,
        "start": {"dateTime": "2026-05-18T11:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-05-18T11:30:00.0000000", "timeZone": "UTC"},
        "organizer": {"emailAddress": {"name": "Dave", "address": "dave@example.com"}},
    }
    client = FakeGraphClient({"value": [no_subject]})
    repo = GraphCalendarRepository(graph_client=cast("GraphClient", cast("object", client)))

    events = repo.list_events("2026-05-18", "2026-05-18")

    assert len(events) == 1
    assert events[0].subject == "(No subject)"
