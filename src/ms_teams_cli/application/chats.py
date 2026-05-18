"""Chat application services."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.entities import Chat, ChatMessage, ChatType
from ms_teams_cli.domain.services import classify_chat, is_unread, resolve_display_name, strip_html

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.chat import ChatServiceClient


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

    def list_unread(self, chat_type: ChatType | None = None) -> list[Chat]:
        """Return conversations with unread messages."""
        chat_service_url = self._client.get_service_url()
        url = f"{chat_service_url}/v1/users/ME/conversations?view=mychats&pageSize=200"
        data = self._client.get(url)
        conversations = _as_payloads(data.get("conversations", []))
        unread = [c for c in conversations if is_unread(c)]
        if chat_type is not None:
            unread = [c for c in unread if classify_chat(str(c.get("id", ""))) == chat_type]

        result: list[Chat] = []
        for conv in unread:
            conv_id = str(conv.get("id", ""))
            ctype = classify_chat(conv_id)
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

    def resolve_chat_name(self, chat_id: str) -> str:
        """Resolve a chat ID to a display name by searching conversations."""
        chat_service_url = self._client.get_service_url()
        try:
            url = f"{chat_service_url}/v1/users/ME/conversations?view=mychats&pageSize=200"
            data = self._client.get(url)
            for conv in _as_payloads(data.get("conversations", [])):
                if conv.get("id") == chat_id:
                    return resolve_display_name(conv, self._client, chat_service_url)
        except Exception:  # noqa: BLE001
            pass
        return chat_id  # Fall back to raw ID

    def send_message(self, chat_id: str, message: str) -> str:
        """Send a message to a chat conversation. Returns the message ID."""
        chat_service_url = self._client.get_service_url()
        url = f"{chat_service_url}/v1/users/ME/conversations/{chat_id}/messages"
        body: dict[str, object] = {
            "content": message,
            "messagetype": "RichText/Html" if "<" in message else "Text",
            "contenttype": "text",
        }
        result = self._client.post(url, body)
        return str(result.get("OriginalArrivalTime") or result.get("id", ""))

    def get_messages(self, chat_id: str, top: int = 30) -> list[ChatMessage]:
        """Return messages from a chat conversation in chronological order."""
        chat_service_url = self._client.get_service_url()
        url = f"{chat_service_url}/v1/users/ME/conversations/{chat_id}/messages?pageSize={top}"
        data = self._client.get(url)
        messages = _as_payloads(data.get("messages", []))
        allowed_types = {"Text", "RichText", "RichText/Html"}
        user_msgs = [m for m in messages if m.get("messagetype") in allowed_types]
        # API returns newest-first; reverse to chronological
        user_msgs.reverse()
        return [ChatMessage.model_validate(m) for m in user_msgs]
