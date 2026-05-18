"""Graph-backed calendar repository adapter."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.entities import CalendarEvent

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.graph.client import GraphClient

_GRAPH = "https://graph.microsoft.com/v1.0"


def _as_event_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


class GraphCalendarRepository:
    """Infrastructure adapter implementing CalendarRepository via Microsoft Graph API."""

    def __init__(self, graph_client: GraphClient) -> None:
        self._client: GraphClient = graph_client

    def list_events(self, start_date: str, end_date: str) -> list[CalendarEvent]:
        """Return all calendar events within the given date range (inclusive)."""
        url: str | None = (
            f"{_GRAPH}/me/calendarView"
            f"?startDateTime={start_date}T00:00:00"
            f"&endDateTime={end_date}T23:59:59"
            f"&$orderby=start/dateTime"
            f"&$top=100"
            f"&$select=id,subject,start,end,isAllDay,organizer,isCancelled"
        )
        results: list[CalendarEvent] = []
        while url is not None:
            data = self._client.get(url)
            for item in _as_event_payloads(data.get("value", [])):
                event = self._parse_event(item)
                if event is not None:
                    results.append(event)
            next_link = data.get("@odata.nextLink")
            url = str(next_link) if isinstance(next_link, str) else None
        return results

    def _parse_event(self, item: dict[str, object]) -> CalendarEvent | None:
        if item.get("isCancelled") is True:
            return None
        start = cast("dict[str, object]", item.get("start") or {})
        end = cast("dict[str, object]", item.get("end") or {})
        org = cast("dict[str, object]", item.get("organizer") or {})
        email = cast("dict[str, object]", org.get("emailAddress") or {})
        return CalendarEvent(
            id=str(item.get("id", "")),
            subject=str(item.get("subject") or "(No subject)"),
            start_datetime=str(start.get("dateTime", "")),
            end_datetime=str(end.get("dateTime", "")),
            start_timezone=str(start.get("timeZone") or "UTC"),
            end_timezone=str(end.get("timeZone") or "UTC"),
            is_all_day=bool(item.get("isAllDay", False)),
            organizer_name=str(email.get("name") or ""),
            is_cancelled=False,
        )
