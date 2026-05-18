"""Resolve chat name use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.ports import ChatRepository


class ResolveChatNameUseCase:
    def __init__(self, repo: ChatRepository) -> None:
        self._repo = repo

    def execute(self, chat_id: str) -> str:
        return self._repo.resolve_chat_name(chat_id)
