"""MCP server configuration — allowlist for send_message tool."""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast


def _config_path() -> Path:
    return Path.home() / ".config" / "ms-teams-cli" / "mcp.json"


def load_allowed_chats() -> set[str]:
    """Load allowed chat IDs from config file.

    Reads ~/.config/ms-teams-cli/mcp.json expecting:
        {"allowed_chats": ["19:xxx@unq.gbl.spaces", ...]}

    Returns empty set if file is missing, unreadable, or malformed.
    Empty set = block ALL sends (safe by default).
    """
    path = _config_path()
    if not path.exists():
        return set()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return set()
        data_dict = cast("dict[str, object]", data)
        allowed_raw = data_dict.get("allowed_chats", [])
        if not isinstance(allowed_raw, list):
            return set()
        allowed = cast("list[object]", allowed_raw)
        return {str(item) for item in allowed if isinstance(item, str)}
    except (OSError, json.JSONDecodeError):
        return set()


def is_chat_allowed(chat_id: str) -> bool:
    return chat_id in load_allowed_chats()
