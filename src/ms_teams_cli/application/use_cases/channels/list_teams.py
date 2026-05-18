"""List teams use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import Team
    from ms_teams_cli.domain.ports import ChannelRepository


class ListTeamsUseCase:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    def execute(self) -> list[Team]:
        return self._repo.list_teams()
