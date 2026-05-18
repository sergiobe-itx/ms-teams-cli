"""Find unanswered messages use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import ChannelMessage
    from ms_teams_cli.domain.ports import ChannelRepository


class FindUnansweredUseCase:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    def execute(
        self,
        team_id: str,
        channel_id: str,
        minutes: int = 120,
    ) -> list[ChannelMessage]:
        return self._repo.find_unanswered(
            team_id=team_id,
            channel_id=channel_id,
            minutes=minutes,
        )
