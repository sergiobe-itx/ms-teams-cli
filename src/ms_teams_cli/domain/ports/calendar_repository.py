"""Calendar repository protocol for ms-teams-cli."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import CalendarEvent


class CalendarRepository(Protocol):
    """Protocol for calendar data access."""

    def list_events(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        """Return calendar events within the given date range."""
        ...
