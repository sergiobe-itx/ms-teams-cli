"""Chat-related CLI commands."""
from __future__ import annotations

import sys
from typing import Annotated, cast

import typer

from ms_teams_cli.domain.exceptions import TeamsError
from ms_teams_cli.presentation.cli._app import app


@app.command("chats")
def chats_command(
    chat_type: Annotated[
        str | None,
        typer.Option("--type", help="Filter by chat type: group|1:1|meeting|other"),  # pyright: ignore[reportUnknownMemberType]
    ] = None,
    top: Annotated[
        int,
        typer.Option("--top", help="Number of chats to fetch"),  # pyright: ignore[reportUnknownMemberType]
    ] = 50,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List chats from the Teams chat service."""
    from ms_teams_cli.domain.entities import ChatType
    from ms_teams_cli.presentation.cli.formatters import format_chats_table, format_json
    from ms_teams_cli.presentation.dependencies import get_list_chats

    resolved_type: ChatType | None = None
    if chat_type is not None:
        try:
            resolved_type = ChatType(chat_type)
        except ValueError as exc:
            typer.echo(f"Invalid chat type: {chat_type}", err=True)
            raise typer.Exit(code=1) from exc

    try:
        chats = get_list_chats().execute(top=top, chat_type=resolved_type)
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(chats)
        return

    format_chats_table(chats)


@app.command("unread")
def unread_command(
    chat_type: Annotated[
        str | None,
        typer.Option("--type", help="Filter by chat type: group|1:1|meeting|other"),  # pyright: ignore[reportUnknownMemberType]
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List chats with unread messages."""
    from ms_teams_cli.domain.entities import ChatType
    from ms_teams_cli.presentation.cli.formatters import format_json, format_unread_table
    from ms_teams_cli.presentation.dependencies import get_list_unread

    resolved_type: ChatType | None = None
    if chat_type is not None:
        try:
            resolved_type = ChatType(chat_type)
        except ValueError as exc:
            typer.echo(f"Invalid chat type: {chat_type}", err=True)
            raise typer.Exit(code=1) from exc

    try:
        chats = get_list_unread().execute(chat_type=resolved_type)
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(chats)
        return

    format_unread_table(chats)


@app.command("chat-messages")
def chat_messages_command(
    chat_id: Annotated[
        str,
        typer.Option("--chat", help="Conversation ID"),  # pyright: ignore[reportUnknownMemberType]
    ],
    top: Annotated[
        int,
        typer.Option("--top", help="Number of messages to fetch"),  # pyright: ignore[reportUnknownMemberType]
    ] = 30,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """Show messages from a chat conversation."""
    from ms_teams_cli.presentation.cli.formatters import format_chat_messages_table, format_json
    from ms_teams_cli.presentation.dependencies import get_chat_messages

    try:
        messages = get_chat_messages().execute(chat_id=chat_id, top=top)
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(messages)
        return

    format_chat_messages_table(messages)


@app.command("send-message")
def send_message_command(
    chat_id: Annotated[str, typer.Option("--chat", help="Conversation ID")],  # pyright: ignore[reportUnknownMemberType]
    message: Annotated[str, typer.Option("--message", help="Text to send")],  # pyright: ignore[reportUnknownMemberType]
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,  # pyright: ignore[reportUnknownMemberType]
) -> None:
    """Send a message to a chat conversation."""
    from ms_teams_cli.presentation.dependencies import get_resolve_chat_name, get_send_message

    try:
        chat_name = get_resolve_chat_name().execute(chat_id)
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("=" * 60)
    typer.echo(f"  TO:      {chat_name}")
    typer.echo(f"  CHAT ID: {chat_id}")
    typer.echo(f"  MESSAGE: {message}")
    typer.echo("=" * 60)

    if yes:
        confirmed = True
    elif sys.stdin.isatty():
        answer = cast(
            "str",
            typer.prompt("\nSend this message? [y/N]", default="N"),
        )
        confirmed = answer.strip().lower() == "y"
    else:
        confirmed = True

    if not confirmed:
        typer.echo("Cancelled — message NOT sent.")
        return

    try:
        msg_id = get_send_message().execute(chat_id, message)
        typer.echo(f"Message sent. (id: {msg_id})")
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
