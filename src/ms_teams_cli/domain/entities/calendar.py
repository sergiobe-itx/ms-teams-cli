"""Calendar event entity."""
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class CalendarEvent(BaseModel):
    """A Microsoft Teams calendar event."""

    id: str
    subject: str = Field(default="(No subject)")
    start_datetime: str
    end_datetime: str
    start_timezone: str = Field(default="UTC")
    end_timezone: str = Field(default="UTC")
    is_all_day: bool = Field(default=False)
    organizer_name: str = Field(default="")
    is_cancelled: bool = Field(default=False)

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
