"""MCP server — exposes ms-teams-cli use cases as agent-callable tools."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingModuleSource]

from ms_teams_cli.domain.entities import ChatType
from ms_teams_cli.domain.exceptions import TeamsError
from ms_teams_cli.mcp_config import is_chat_allowed
from ms_teams_cli.presentation.dependencies import (
    get_chat_messages,
    get_find_unanswered,
    get_get_messages,
    get_get_thread,
    get_list_calendar_events,
    get_list_channels,
    get_list_chats,
    get_list_teams,
    get_list_unread,
    get_resolve_chat_name,
    get_scan_activity,
    get_send_message,
)

mcp: FastMCP = FastMCP("ms-teams", json_response=True)  # pyright: ignore[reportUnknownVariableType]


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_list_chats(top: int = 50, chat_type: str | None = None) -> str:
    resolved: ChatType | None = None
    if chat_type is not None:
        try:
            resolved = ChatType(chat_type)
        except ValueError:
            valid = "1:1, group, meeting, other"
            return json.dumps({"error": f"Invalid chat_type '{chat_type}'. Valid values: {valid}"})
    try:
        chats = get_list_chats().execute(top=top, chat_type=resolved)
        return json.dumps([c.model_dump() for c in chats], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_list_unread(chat_type: str | None = None) -> str:
    resolved: ChatType | None = None
    if chat_type is not None:
        try:
            resolved = ChatType(chat_type)
        except ValueError:
            valid = "1:1, group, meeting, other"
            return json.dumps({"error": f"Invalid chat_type '{chat_type}'. Valid values: {valid}"})
    try:
        chats = get_list_unread().execute(chat_type=resolved)
        return json.dumps([c.model_dump() for c in chats], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_get_chat_messages(chat_id: str, top: int = 30) -> str:
    try:
        messages = get_chat_messages().execute(chat_id=chat_id, top=top)
        return json.dumps([m.model_dump() for m in messages], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_send_message(chat_id: str, message: str) -> str:
    if not is_chat_allowed(chat_id):
        return json.dumps({
            "error": (
                f"Chat '{chat_id}' is not in the send allowlist. "
                "Add it to ~/.config/ms-teams-cli/mcp.json under 'allowed_chats'."
            )
        })
    try:
        msg_id = get_send_message().execute(chat_id, message)
        return json.dumps({"message_id": msg_id})
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_resolve_chat_name(chat_id: str) -> str:
    try:
        name = get_resolve_chat_name().execute(chat_id)
        return json.dumps({"name": name})
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_list_teams() -> str:
    try:
        teams = get_list_teams().execute()
        return json.dumps([t.model_dump() for t in teams], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_list_channels(team_id: str) -> str:
    try:
        channels = get_list_channels().execute(team_id)
        return json.dumps([c.model_dump() for c in channels], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_get_channel_messages(
    team_id: str,
    channel_id: str,
    top: int = 20,
    pages: int = 1,
    since: str | None = None,
) -> str:
    try:
        messages = list(get_get_messages().execute(
            team_id=team_id,
            channel_id=channel_id,
            top=top,
            pages=pages,
            since=since,
        ))
        return json.dumps([m.model_dump() for m in messages], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_get_thread(
    team_id: str,
    channel_id: str,
    message_id: str,
    top: int = 50,
) -> str:
    try:
        parent, replies = get_get_thread().execute(
            team_id=team_id,
            channel_id=channel_id,
            message_id=message_id,
            top=top,
        )
        return json.dumps(
            {"parent": parent.model_dump(), "replies": [r.model_dump() for r in replies]},
            default=str,
        )
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_find_unanswered(team_id: str, channel_id: str, minutes: int = 120) -> str:
    try:
        messages = get_find_unanswered().execute(
            team_id=team_id,
            channel_id=channel_id,
            minutes=minutes,
        )
        return json.dumps([m.model_dump() for m in messages], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_scan_activity(team_id: str, date: str, pages: int = 2, top: int = 50) -> str:
    try:
        result = get_scan_activity().execute(
            team_id=team_id,
            date=date,
            pages=pages,
            top=top,
        )
        return json.dumps(result.model_dump(), default=str)
    except (TeamsError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()  # pyright: ignore[reportUnknownMemberType]
def teams_list_calendar_events(start_date: str, end_date: str) -> str:
    try:
        events = get_list_calendar_events().execute(start_date, end_date)
        return json.dumps([e.model_dump() for e in events], default=str)
    except TeamsError as exc:
        return json.dumps({"error": str(exc)})


def main() -> None:
    mcp.run(transport="stdio")  # pyright: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    main()
