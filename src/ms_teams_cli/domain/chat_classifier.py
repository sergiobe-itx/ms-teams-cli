"""Chat conversation classification utilities."""
from __future__ import annotations

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
