"""Domain models for ms-teams-cli."""
from __future__ import annotations

from typing import ClassVar, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Team(BaseModel):
    """A Microsoft Teams team."""

    id: str
    display_name: str = Field(alias="displayName")
    description: str | None = Field(default=None, alias="description")

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)


class Channel(BaseModel):
    """A Microsoft Teams channel."""

    id: str
    display_name: str = Field(alias="displayName")
    description: str | None = Field(default=None, alias="description")

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)


class MessageAuthor(BaseModel):
    """Author of a Teams channel message, extracted from the nested 'from.user' path."""

    display_name: str = Field(default="(bot)", alias="displayName")

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)


class MessageBody(BaseModel):
    """Body content of a Teams channel message."""

    content: str = Field(default="")
    content_type: str = Field(default="text", alias="contentType")

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)


class ChannelMessage(BaseModel):
    """A message in a Microsoft Teams channel."""

    id: str
    created_date_time: str = Field(alias="createdDateTime")
    author: MessageAuthor = Field(default_factory=lambda: MessageAuthor(displayName="(bot)"))
    body: MessageBody = Field(default_factory=MessageBody)
    reply_count: int | None = Field(default=None, alias="replyCount")
    message_type: str = Field(default="message", alias="messageType")
    reply_to_id: str | None = Field(default=None, alias="replyToId")

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def extract_author(cls, data: object) -> object:
        """Extract author display name from nested from.user.displayName path."""
        if not isinstance(data, dict):
            return data
        payload = cast("dict[str, object]", data)
        from_value = payload.get("from")
        from_field: dict[str, object] = (
            cast("dict[str, object]", from_value) if isinstance(from_value, dict) else {}
        )
        user_value = from_field.get("user")
        user_field: dict[str, object] = (
            cast("dict[str, object]", user_value) if isinstance(user_value, dict) else {}
        )
        display_name_value = user_field.get("displayName")
        display_name = display_name_value if isinstance(display_name_value, str) else "(bot)"
        result = dict(payload)
        if "author" not in result:
            result["author"] = {"displayName": display_name}
        return result


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
