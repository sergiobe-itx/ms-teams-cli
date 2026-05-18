"""List calendar events use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import CalendarEvent
    from ms_teams_cli.domain.ports import CalendarRepository


class ListCalendarEventsUseCase:
    def __init__(self, repo: CalendarRepository) -> None:
        self._repo = repo

    def execute(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        return self._repo.list_events(start_date, end_date)
