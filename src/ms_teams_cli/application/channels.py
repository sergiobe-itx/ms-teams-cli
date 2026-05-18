"""Channel application services."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.models import Channel, Team

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.graph_client import GraphClient


_GRAPH = "https://graph.microsoft.com/v1.0"
_TEAMS_URL = f"{_GRAPH}/me/joinedTeams?$select=id,displayName,description"
_CHANNELS_URL = "{_GRAPH}/teams/{team_id}/channels?$select=id,displayName,description"


def _as_team_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


def _as_channel_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


class ChannelService:
    """Application service for Microsoft Teams channel operations."""

    def __init__(self, graph_client: GraphClient) -> None:
        self._client: GraphClient = graph_client

    def list_teams(self) -> list[Team]:
        """Return all teams the authenticated user is a member of."""
        data = self._client.get(_TEAMS_URL)
        return [Team.model_validate(item) for item in _as_team_payloads(data.get("value", []))]

    def list_channels(self, team_id: str) -> list[Channel]:
        """Return all channels for the given team."""
        url = f"{_GRAPH}/teams/{team_id}/channels?$select=id,displayName,description"
        data = self._client.get(url)
        payloads = _as_channel_payloads(data.get("value", []))
        return [Channel.model_validate(item) for item in payloads]
