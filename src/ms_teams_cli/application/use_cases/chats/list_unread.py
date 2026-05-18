"""List unread chats use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import Chat, ChatType
    from ms_teams_cli.domain.ports import ChatRepository


class ListUnreadUseCase:
    def __init__(self, repo: ChatRepository) -> None:
        self._repo = repo

    def execute(self, chat_type: ChatType | None = None) -> list[Chat]:
        return self._repo.list_unread(chat_type=chat_type)
