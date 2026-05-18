"""Chat repository protocol for ms-teams-cli."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import Chat, ChatMessage, ChatType


class ChatRepository(Protocol):
    """Protocol for chat data access."""

    def list_chats(
        self,
        top: int = 50,
        chat_type: ChatType | None = None,
    ) -> list[Chat]:
        """Return a list of chats, optionally filtered by type."""
        ...

    def list_unread(self, chat_type: ChatType | None = None) -> list[Chat]:
        """Return conversations with unread messages."""
        ...

    def get_messages(self, chat_id: str, top: int = 30) -> list[ChatMessage]:
        """Return messages from a chat conversation in chronological order."""
        ...

    def send_message(self, chat_id: str, message: str) -> str:
        """Send a message to a chat conversation. Returns the message ID."""
        ...

    def resolve_chat_name(self, chat_id: str) -> str:
        """Resolve a chat ID to a display name by searching conversations."""
        ...
