"""Graph-backed chat repository adapter."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.entities import Chat, ChatMessage, ChatType
from ms_teams_cli.domain.services.text import strip_html

if TYPE_CHECKING:
    from ms_teams_cli.infrastructure.graph.client import GraphClient

_GRAPH = "https://graph.microsoft.com/v1.0"

_CHAT_TYPE_MAP: dict[str, ChatType] = {
    "oneOnOne": ChatType.ONE_TO_ONE,
    "group": ChatType.GROUP,
    "meeting": ChatType.MEETING,
}


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _as_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


class GraphChatRepository:
    """Infrastructure adapter implementing ChatRepository via Microsoft Graph API."""

    def __init__(self, graph_client: GraphClient) -> None:
        self._client: GraphClient = graph_client
        self._current_user_id: str | None = None

    def _get_current_user_id(self) -> str:
        if self._current_user_id is None:
            data = self._client.get(f"{_GRAPH}/me")
            self._current_user_id = str(data.get("id", ""))
        return self._current_user_id

    def _parse_chat(self, item: dict[str, object], my_id: str) -> Chat:
        chat_id = str(item.get("id", ""))
        chat_type = _CHAT_TYPE_MAP.get(str(item.get("chatType", "")), ChatType.OTHER)
        topic = str(item.get("topic") or "")
        members = _as_list(item.get("members"))

        if topic:
            display_name = topic
        elif chat_type is ChatType.ONE_TO_ONE:
            display_name = next(
                (
                    str(member.get("displayName") or "")
                    for member in members
                    if str(member.get("userId") or "") != my_id and member.get("displayName")
                ),
                "",
            )
        elif chat_type is ChatType.GROUP:
            display_name = ", ".join(
                str(member.get("displayName") or "")
                for member in members
                if member.get("displayName")
            )
        else:
            display_name = ""

        if not display_name:
            display_name = chat_id[:40]

        last_preview = _as_dict(item.get("lastMessagePreview"))
        preview_body = _as_dict(last_preview.get("body"))
        raw_content = str(preview_body.get("content") or "")
        content_type = str(preview_body.get("contentType") or "text")
        preview_text = strip_html(raw_content) if content_type == "html" else raw_content
        last_message_preview = preview_text[:80] or None
        last_message_time = str(last_preview.get("createdDateTime") or "") or None

        return Chat(
            id=chat_id,
            chat_type=chat_type,
            display_name=display_name,
            last_message_preview=last_message_preview,
            last_message_time=last_message_time,
        )

    def list_chats(self, top: int = 50, chat_type: ChatType | None = None) -> list[Chat]:
        my_id = self._get_current_user_id()
        url = (
            f"{_GRAPH}/me/chats"
            f"?$expand=members,lastMessagePreview"
            f"&$top={top}"
            f"&$orderby=lastMessagePreview/createdDateTime desc"
        )
        data = self._client.get(url)
        chats = _as_list(data.get("value"))
        result: list[Chat] = []
        for item in chats:
            chat = self._parse_chat(item, my_id)
            if chat_type is not None and chat.chat_type != chat_type:
                continue
            result.append(chat)
        return result

    def list_unread(self, chat_type: ChatType | None = None) -> list[Chat]:
        my_id = self._get_current_user_id()
        url = (
            f"{_GRAPH}/me/chats"
            f"?$expand=members,lastMessagePreview"
            f"&$top=200"
            f"&$orderby=lastMessagePreview/createdDateTime desc"
        )
        data = self._client.get(url)
        chats = _as_list(data.get("value"))
        result: list[Chat] = []
        for item in chats:
            viewpoint = _as_dict(item.get("viewpoint"))
            last_read = str(viewpoint.get("lastMessageReadDateTime") or "")
            last_preview = _as_dict(item.get("lastMessagePreview"))
            last_msg_time = str(last_preview.get("createdDateTime") or "")
            has_message = bool(last_msg_time)
            is_unread = (not last_read and has_message) or (
                bool(last_read) and has_message and last_msg_time > last_read
            )
            if not is_unread:
                continue
            chat = self._parse_chat(item, my_id)
            if chat_type is not None and chat.chat_type != chat_type:
                continue
            result.append(chat)
        return result

    def get_messages(self, chat_id: str, top: int = 30) -> list[ChatMessage]:
        url = f"{_GRAPH}/me/chats/{chat_id}/messages?$top={top}"
        data = self._client.get(url)
        messages = _as_list(data.get("value"))
        allowed_content_types = {"text", "html"}
        user_msgs: list[dict[str, object]] = []
        for msg in messages:
            if msg.get("eventMessageDetail") is not None:
                continue
            body = _as_dict(msg.get("body"))
            content_type = str(body.get("contentType") or "")
            if content_type not in allowed_content_types:
                continue
            user_msgs.append(msg)

        user_msgs.reverse()
        result: list[ChatMessage] = []
        for msg in user_msgs:
            body = _as_dict(msg.get("body"))
            content_type = str(body.get("contentType") or "text")
            raw_content = str(body.get("content") or "")
            content = strip_html(raw_content) if content_type == "html" else raw_content
            from_info = _as_dict(msg.get("from"))
            user_info = _as_dict(from_info.get("user"))
            sender_name = str(user_info.get("displayName") or "(unknown)")
            result.append(
                ChatMessage.model_construct(
                    id=str(msg.get("id", "")),
                    compose_time=str(msg.get("createdDateTime") or ""),
                    sender_name=sender_name,
                    content=content,
                    message_type="RichText/Html" if content_type == "html" else "Text",
                )
            )
        return result

    def send_message(self, chat_id: str, message: str) -> str:
        url = f"{_GRAPH}/me/chats/{chat_id}/messages"
        content_type = "html" if "<" in message else "text"
        body: dict[str, object] = {"body": {"content": message, "contentType": content_type}}
        result = self._client.post(url, body)
        return str(result.get("id", ""))

    def resolve_chat_name(self, chat_id: str) -> str:
        try:
            url = f"{_GRAPH}/me/chats/{chat_id}?$expand=members"
            data = self._client.get(url)
            topic = str(data.get("topic") or "")
            if topic:
                return topic
            my_id = self._get_current_user_id()
            members = _as_list(data.get("members"))
            names = [
                str(member.get("displayName") or "")
                for member in members
                if str(member.get("userId") or "") != my_id and member.get("displayName")
            ]
            if names:
                return ", ".join(names)
        except Exception:  # noqa: BLE001
            pass
        return chat_id
