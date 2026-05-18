"""Microsoft Teams CLI and Python library."""
from __future__ import annotations

from loguru import logger

from ms_teams_cli.application.channels import ChannelService
from ms_teams_cli.application.chats import ChatService
from ms_teams_cli.domain.exceptions import APIError, AuthenticationError, TeamsError
from ms_teams_cli.domain.models import Channel, ChannelMessage, Chat, ChatMessage, ScanResult, Team

__version__ = "0.1.0"

logger.disable("ms_teams_cli")

__all__ = [
    "__version__",
    "ChannelService",
    "ChatService",
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
