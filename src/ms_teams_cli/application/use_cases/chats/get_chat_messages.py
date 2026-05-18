"""Get chat messages use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import ChatMessage
    from ms_teams_cli.domain.ports import ChatRepository


class GetChatMessagesUseCase:
    def __init__(self, repo: ChatRepository) -> None:
        self._repo = repo

    def execute(self, chat_id: str, top: int = 30) -> list[ChatMessage]:
        return self._repo.get_messages(chat_id, top=top)
