"""Chat entities."""
from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class ChatType(StrEnum):
    """Classification of a Teams chat conversation."""

    ONE_TO_ONE = "1:1"
    GROUP = "group"
    MEETING = "meeting"
    OTHER = "other"


class Chat(BaseModel):
    """A Teams chat conversation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    id: str
    chat_type: ChatType
    display_name: str
    last_message_preview: str | None = None
    last_message_time: str | None = None


class ChatMessage(BaseModel):
    """A message in a Teams chat conversation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    id: str
    compose_time: str = Field(default="", alias="composetime")
    sender_name: str = Field(default="(unknown)", alias="imdisplayname")
    content: str = Field(default="")
    message_type: str = Field(default="Text", alias="messagetype")
