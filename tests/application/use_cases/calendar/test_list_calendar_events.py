"""Tests for ListCalendarEventsUseCase."""
from __future__ import annotations

from ms_teams_cli.application.use_cases.calendar import ListCalendarEventsUseCase
from ms_teams_cli.domain.entities import CalendarEvent


class FakeCalendarRepo:
    def __init__(self, events: list[CalendarEvent]) -> None:
        self._events = events
        self.received_args: tuple[str, str] | None = None

    def list_events(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        self.received_args = (start_date, end_date)
        return self._events


def test_list_calendar_events_returns_events() -> None:
    events = [
        CalendarEvent(
            id="1",
            subject="Standup",
            start_datetime="2026-05-18T09:00:00",
            end_datetime="2026-05-18T09:30:00",
            start_timezone="UTC",
            end_timezone="UTC",
        ),
        CalendarEvent(
            id="2",
            subject="Retro",
            start_datetime="2026-05-18T14:00:00",
            end_datetime="2026-05-18T15:00:00",
            start_timezone="UTC",
            end_timezone="UTC",
        ),
    ]
    repo = FakeCalendarRepo(events)
    use_case = ListCalendarEventsUseCase(repo=repo)  # type: ignore[arg-type]
    result = use_case.execute("2026-05-18", "2026-05-18")

    assert result == events
    assert len(result) == 2
    assert result[0].subject == "Standup"
    assert result[1].subject == "Retro"


def test_list_calendar_events_empty() -> None:
    repo = FakeCalendarRepo([])
    use_case = ListCalendarEventsUseCase(repo=repo)  # type: ignore[arg-type]
    assert use_case.execute("2026-05-18", "2026-05-18") == []


def test_list_calendar_events_passes_dates_to_repo() -> None:
    repo = FakeCalendarRepo([])
    use_case = ListCalendarEventsUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute("2026-05-01", "2026-05-31")

    assert repo.received_args == ("2026-05-01", "2026-05-31")
