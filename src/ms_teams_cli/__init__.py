"""Microsoft Teams CLI and Python library."""
from __future__ import annotations

from loguru import logger

from ms_teams_cli.domain.entities import (
    Channel,
    ChannelMessage,
    Chat,
    ChatMessage,
    ScanResult,
    Team,
)
from ms_teams_cli.domain.exceptions import APIError, AuthenticationError, TeamsError
from ms_teams_cli.infrastructure.graph import GraphChannelRepository

__version__ = "0.1.0"

ChannelService = GraphChannelRepository

logger.disable("ms_teams_cli")

__all__ = [
    "__version__",
    "ChannelService",
    "TeamsError",
    "AuthenticationError",
    "APIError",
    "Team",
    "Channel",
    "ChannelMessage",
    "Chat",
    "ChatMessage",
    "ScanResult",
]
