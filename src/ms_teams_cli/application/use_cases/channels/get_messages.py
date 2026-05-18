"""Get messages use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ms_teams_cli.domain.entities import ChannelMessage
    from ms_teams_cli.domain.ports import ChannelRepository


class GetMessagesUseCase:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    def execute(
        self,
        team_id: str,
        channel_id: str,
        top: int = 20,
        pages: int = 1,
        since: str | None = None,
    ) -> Iterator[ChannelMessage]:
        return self._repo.get_messages(
            team_id=team_id,
            channel_id=channel_id,
            top=top,
            pages=pages,
            since=since,
        )
