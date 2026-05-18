"""List channels use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import Channel
    from ms_teams_cli.domain.ports import ChannelRepository


class ListChannelsUseCase:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    def execute(self, team_id: str) -> list[Channel]:
        return self._repo.list_channels(team_id)
