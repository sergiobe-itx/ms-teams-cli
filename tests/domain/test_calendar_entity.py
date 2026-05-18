"""Tests for CalendarEvent entity."""
from __future__ import annotations

from ms_teams_cli.domain.entities import CalendarEvent


def test_calendar_event_defaults() -> None:
    ev = CalendarEvent(
        id="1",
        start_datetime="2026-05-18T09:00:00",
        end_datetime="2026-05-18T09:30:00",
        start_timezone="UTC",
        end_timezone="UTC",
    )
    assert ev.subject == "(No subject)"
    assert ev.is_all_day is False
    assert ev.is_cancelled is False
    assert ev.organizer_name == ""


def test_calendar_event_full() -> None:
    ev = CalendarEvent(
        id="2",
        subject="Standup",
        start_datetime="2026-05-18T09:00:00",
        end_datetime="2026-05-18T09:30:00",
        start_timezone="UTC",
        end_timezone="UTC",
        is_all_day=False,
        organizer_name="Alice",
        is_cancelled=False,
    )
    assert ev.subject == "Standup"
    assert ev.organizer_name == "Alice"


def test_calendar_event_all_day() -> None:
    ev = CalendarEvent(
        id="3",
        subject="Holiday",
        start_datetime="2026-05-18T00:00:00",
        end_datetime="2026-05-19T00:00:00",
        start_timezone="UTC",
        end_timezone="UTC",
        is_all_day=True,
    )
    assert ev.is_all_day is True
