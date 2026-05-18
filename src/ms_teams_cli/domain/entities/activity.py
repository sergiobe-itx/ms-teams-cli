"""Activity entities."""
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from .channel import ChannelMessage  # noqa: TC001


class ThreadActivity(BaseModel):
    """A thread and its replies on a specific date."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    root_message: ChannelMessage
    replies_on_date: list[ChannelMessage]
    root_created_on_date: bool


class ChannelActivity(BaseModel):
    """Activity summary for a single channel on a specific date."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    channel_name: str
    channel_id: str
    threads: list[ThreadActivity]


class ScanResult(BaseModel):
    """Result of scanning all channels for activity on a date."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    date: str
    channels: list[ChannelActivity]
