"""Domain services for ms-teams-cli."""
from __future__ import annotations

from ms_teams_cli.domain.services.chat_classifier import classify_chat, is_unread
from ms_teams_cli.domain.services.chat_display import resolve_display_name
from ms_teams_cli.domain.services.text import format_datetime, strip_html
from ms_teams_cli.domain.services.url_parser import TeamsUrlComponents, parse_teams_url

__all__ = [
    "classify_chat",
    "is_unread",
    "resolve_display_name",
    "format_datetime",
    "strip_html",
    "TeamsUrlComponents",
    "parse_teams_url",
]
