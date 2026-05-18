"""Get thread use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import ChannelMessage
    from ms_teams_cli.domain.ports import ChannelRepository


class GetThreadUseCase:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    def execute(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        top: int = 50,
    ) -> tuple[ChannelMessage, list[ChannelMessage]]:
        return self._repo.get_thread(
            team_id=team_id,
            channel_id=channel_id,
            message_id=message_id,
            top=top,
        )
