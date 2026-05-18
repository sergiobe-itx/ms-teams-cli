"""Chat conversation classification utilities."""
from __future__ import annotations

from typing import cast

from ms_teams_cli.domain.models import ChatType


def classify_chat(conv_id: str) -> ChatType:
    """Classify a conversation by its ID pattern."""
    if ":meeting_" in conv_id:
        return ChatType.MEETING
    if "thread.v2" in conv_id or "thread.tacv2" in conv_id:
        return ChatType.GROUP
    if "@unq.gbl.spaces" in conv_id:
        return ChatType.ONE_TO_ONE
    if ":8:" in conv_id or ":orgid:" in conv_id:
        return ChatType.ONE_TO_ONE
    return ChatType.OTHER


def is_unread(conv: dict[str, object]) -> bool:
    """Determine if a conversation has unread messages.

    consumptionhorizon format: "ts1;ts2;ts3"
    Compare first value as integer against lastMessage.id as integer.
    - No lastMessage → not unread (no messages to read)
    - No horizon → unread (never opened)
    - last_id > horizon_ts → unread
    - Parse errors → unread (safe default)
    """
    props = conv.get("properties")
    props_dict = cast("dict[str, object]", props) if isinstance(props, dict) else {}
    horizon = str(props_dict.get("consumptionhorizon", ""))
    last_msg = conv.get("lastMessage")
    last_msg_dict = cast("dict[str, object]", last_msg) if isinstance(last_msg, dict) else {}
    last_id = str(last_msg_dict.get("id", ""))

    if not last_id:
        return False  # No messages at all

    if not horizon:
        return True  # Never opened → unread

    try:
        horizon_ts = horizon.split(";")[0]
        return int(last_id) > int(horizon_ts)
    except (ValueError, IndexError):
        return True  # Can't parse → assume unread
