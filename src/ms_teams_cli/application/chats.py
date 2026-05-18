"""Chat application services."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.chat_classifier import classify_chat
from ms_teams_cli.domain.chat_display import resolve_display_name
from ms_teams_cli.domain.models import Chat, ChatType
from ms_teams_cli.domain.text import strip_html

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.chat_client import ChatServiceClient


def _as_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


class ChatService:
    """Application service for Teams Chat (Skype) operations."""

    def __init__(self, chat_client: ChatServiceClient) -> None:
        self._client: ChatServiceClient = chat_client

    def list_chats(
        self,
        top: int = 50,
        chat_type: ChatType | None = None,
    ) -> list[Chat]:
        """Return a list of chats, optionally filtered by type."""
        chat_service_url = self._client.get_service_url()
        url = f"{chat_service_url}/v1/users/ME/conversations?view=mychats&pageSize={top}"
        data = self._client.get(url)
        conversations = _as_payloads(data.get("conversations", []))

        result: list[Chat] = []
        for conv in conversations:
            conv_id = str(conv.get("id", ""))
            ctype = classify_chat(conv_id)
            if chat_type is not None and ctype != chat_type:
                continue

            display_name = resolve_display_name(conv, self._client, chat_service_url)
            last_message = conv.get("lastMessage")
            last_message_dict = (
                cast("dict[str, object]", last_message) if isinstance(last_message, dict) else {}
            )
            last_message_time = str(last_message_dict.get("composetime", "")) or None
            preview_content = str(last_message_dict.get("content", ""))
            last_message_preview = strip_html(preview_content)[:80] or None

            result.append(
                Chat(
                    id=conv_id,
                    chat_type=ctype,
                    display_name=display_name,
                    last_message_time=last_message_time,
                    last_message_preview=last_message_preview,
                )
            )
        return result
