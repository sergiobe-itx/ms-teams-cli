"""Domain services for ms-teams-cli."""
from __future__ import annotations

from ms_teams_cli.domain.services.text import format_datetime, strip_html
from ms_teams_cli.domain.services.url_parser import TeamsUrlComponents, parse_teams_url

__all__ = [
    "format_datetime",
    "strip_html",
    "TeamsUrlComponents",
    "parse_teams_url",
]
