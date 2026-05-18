"""Send message use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.ports import ChatRepository


class SendMessageUseCase:
    def __init__(self, repo: ChatRepository) -> None:
        self._repo = repo

    def execute(self, chat_id: str, message: str) -> str:
        prefixed = message if message.startswith("🤖") else f"🤖 {message}"
        return self._repo.send_message(chat_id, prefixed)
