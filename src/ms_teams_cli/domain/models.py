"""Domain models for ms-teams-cli."""
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


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
