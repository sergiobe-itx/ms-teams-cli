"""Display name resolution for Teams chat conversations."""
from __future__ import annotations

from typing import Protocol, cast


class _MessageFetcher(Protocol):
    """Protocol for fetching messages from a conversation."""

    def get(self, url: str) -> dict[str, object]:
        """Fetch a URL and return its JSON payload."""
        ...


def resolve_display_name(
    conv: dict[str, object],
    chat_client: _MessageFetcher,
    chat_service_url: str,
) -> str:
    """Best-effort display name for a chat conversation."""
    from ms_teams_cli.domain.entities import ChatType
    from ms_teams_cli.domain.services.chat_classifier import classify_chat

    thread_properties = _as_dict(conv.get("threadProperties"))
    topic = str(thread_properties.get("topic", ""))
    if topic:
        return topic

    last_msg = _as_dict(conv.get("lastMessage"))
    sender = str(last_msg.get("imdisplayname", ""))
    my_name = str(last_msg.get("fromDisplayNameInToken", ""))
    is_my_own = bool(sender and my_name and sender == my_name)

    if sender and not is_my_own:
        return f"Chat with {sender}"

    conv_id = str(conv.get("id", ""))
    is_one_to_one = (
        classify_chat(conv_id) == ChatType.ONE_TO_ONE
        or thread_properties.get("productThreadType") == "OneToOneChat"
    )
    if is_one_to_one and conv_id and chat_service_url:
        other = _resolve_other_person(conv_id, my_name, chat_client, chat_service_url)
        if other:
            return f"Chat with {other}"

    if sender:
        return f"Chat with {sender}"

    return str(conv.get("id", "(unknown)"))[:40]


def _resolve_other_person(
    conv_id: str,
    my_name: str,
    chat_client: _MessageFetcher,
    chat_service_url: str,
) -> str:
    """Fetch recent messages to find the other person's name."""
    try:
        url = f"{chat_service_url}/v1/users/ME/conversations/{conv_id}/messages?pageSize=10"
        data = chat_client.get(url)
        for msg in _as_list(data.get("messages")):
            if not isinstance(msg, dict):
                continue
            payload = cast("dict[str, object]", msg)
            name = str(payload.get("imdisplayname", ""))
            if name and name != my_name:
                return name
    except Exception:  # noqa: BLE001
        pass
    return ""


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast("list[object]", value)
    return []
