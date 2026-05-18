"""CLI entry point for ms-teams."""
from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Annotated, cast, override

import typer
from loguru import logger
from typer.core import TyperGroup

from ms_teams_cli.domain.exceptions import TeamsError

if TYPE_CHECKING:
    from collections.abc import Sequence as SequenceCollection


class TeamsTyperGroup(TyperGroup):
    """Typer group with consistent top-level error handling."""

    @override
    def main(
        self,
        args: SequenceCollection[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: object,
    ) -> object:
        try:
            return cast(
                "object",
                super().main(
                    args=args,
                    prog_name=prog_name,
                    complete_var=complete_var,
                    standalone_mode=standalone_mode,
                    windows_expand_args=windows_expand_args,
                    **extra,
                ),
            )
        except SystemExit as exc:
            if exc.code != 130:
                raise
            typer.echo("Cancelled.", err=True)
            raise SystemExit(130) from exc
        except TeamsError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc


app = typer.Typer(
    name="ms-teams",
    help="Microsoft Teams CLI — read channels and chats.",
    cls=TeamsTyperGroup,
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: Annotated[
        int,
        typer.Option(  # pyright: ignore[reportUnknownMemberType]
            "--verbose",
            "-v",
            count=True,
            help="Increase verbosity (repeatable).",
        ),
    ] = 0,
) -> None:
    """Microsoft Teams CLI."""
    if verbose == 0:
        logger.disable("ms_teams_cli")
    else:
        logger.enable("ms_teams_cli")


@app.command()
def version() -> None:
    """Show version."""
    from ms_teams_cli import __version__

    typer.echo(f"ms-teams-cli {__version__}")


@app.command("teams")
def teams_command(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List all teams the user belongs to."""
    from ms_teams_cli.application.channels import ChannelService
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.graph_client import GraphClient
    from ms_teams_cli.infrastructure.token_cache import TokenCache
    from ms_teams_cli.presentation.formatters import format_json, format_teams_table

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        client = GraphClient(token_provider=provider)
        service = ChannelService(graph_client=client)
        teams = service.list_teams()
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(teams)
        return

    format_teams_table(teams)


@app.command("channels")
def channels_command(
    team_id: Annotated[str, typer.Option("--team", help="Team ID")],  # pyright: ignore[reportUnknownMemberType]
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List channels in a team."""
    from ms_teams_cli.application.channels import ChannelService
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.graph_client import GraphClient
    from ms_teams_cli.infrastructure.token_cache import TokenCache
    from ms_teams_cli.presentation.formatters import format_channels_table, format_json

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        client = GraphClient(token_provider=provider)
        service = ChannelService(graph_client=client)
        channels = service.list_channels(team_id)
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(channels)
        return

    format_channels_table(channels)


@app.command("messages")
def messages_command(
    team_id: Annotated[str, typer.Option("--team", help="Team ID")],  # pyright: ignore[reportUnknownMemberType]
    channel_id: Annotated[
        str,
        typer.Option("--channel", help="Channel ID"),  # pyright: ignore[reportUnknownMemberType]
    ],
    top: Annotated[
        int,
        typer.Option("--top", help="Items per page"),  # pyright: ignore[reportUnknownMemberType]
    ] = 20,
    pages: Annotated[
        int,
        typer.Option("--pages", help="Max pages to fetch"),  # pyright: ignore[reportUnknownMemberType]
    ] = 1,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Filter since ISO date"),  # pyright: ignore[reportUnknownMemberType]
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List messages in a channel."""
    from ms_teams_cli.application.channels import ChannelService
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.graph_client import GraphClient
    from ms_teams_cli.infrastructure.token_cache import TokenCache
    from ms_teams_cli.presentation.formatters import format_json, format_messages_table

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        client = GraphClient(token_provider=provider)
        service = ChannelService(graph_client=client)
        messages = service.get_messages(
            team_id=team_id,
            channel_id=channel_id,
            top=top,
            pages=pages,
            since=since,
        )
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(list(messages))
        return

    format_messages_table(messages)


@app.command("replies")
def replies_command(
    team_id: Annotated[str, typer.Option("--team", help="Team ID")],  # pyright: ignore[reportUnknownMemberType]
    channel_id: Annotated[
        str,
        typer.Option("--channel", help="Channel ID"),  # pyright: ignore[reportUnknownMemberType]
    ],
    thread_id: Annotated[
        str,
        typer.Option("--thread", help="Parent message ID"),  # pyright: ignore[reportUnknownMemberType]
    ],
    top: Annotated[
        int,
        typer.Option("--top", help="Max replies to fetch"),  # pyright: ignore[reportUnknownMemberType]
    ] = 50,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """Show a thread: original post and all replies."""
    from ms_teams_cli.application.channels import ChannelService
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.graph_client import GraphClient
    from ms_teams_cli.infrastructure.token_cache import TokenCache
    from ms_teams_cli.presentation.formatters import format_json, format_thread

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        client = GraphClient(token_provider=provider)
        service = ChannelService(graph_client=client)
        parent, replies = service.get_thread(
            team_id=team_id,
            channel_id=channel_id,
            message_id=thread_id,
            top=top,
        )
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json({"parent": parent.model_dump(), "replies": [r.model_dump() for r in replies]})
        return

    format_thread(parent, replies)


@app.command("unanswered")
def unanswered_command(
    team_id: Annotated[str, typer.Option("--team", help="Team ID")],  # pyright: ignore[reportUnknownMemberType]
    channel_id: Annotated[
        str,
        typer.Option("--channel", help="Channel ID"),  # pyright: ignore[reportUnknownMemberType]
    ],
    minutes: Annotated[
        int,
        typer.Option("--minutes", help="Look-back window in minutes"),  # pyright: ignore[reportUnknownMemberType]
    ] = 120,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List posts with no replies within the last N minutes."""
    from ms_teams_cli.application.channels import ChannelService
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.graph_client import GraphClient
    from ms_teams_cli.infrastructure.token_cache import TokenCache
    from ms_teams_cli.presentation.formatters import format_json, format_unanswered_table

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        client = GraphClient(token_provider=provider)
        service = ChannelService(graph_client=client)
        messages = service.find_unanswered(
            team_id=team_id,
            channel_id=channel_id,
            minutes=minutes,
        )
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(messages)
        return

    format_unanswered_table(messages, minutes)


@app.command("scan")
def scan_command(
    team_id: Annotated[str, typer.Option("--team", help="Team ID")],  # pyright: ignore[reportUnknownMemberType]
    date: Annotated[
        str,
        typer.Option("--date", help="Target date YYYY-MM-DD"),  # pyright: ignore[reportUnknownMemberType]
    ],
    pages: Annotated[
        int,
        typer.Option("--pages", help="Max pages per channel"),  # pyright: ignore[reportUnknownMemberType]
    ] = 2,
    top: Annotated[
        int,
        typer.Option("--top", help="Items per page"),  # pyright: ignore[reportUnknownMemberType]
    ] = 50,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """Scan all channels of a team for activity on a specific date."""
    from ms_teams_cli.application.channels import ChannelService
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.graph_client import GraphClient
    from ms_teams_cli.infrastructure.token_cache import TokenCache
    from ms_teams_cli.presentation.formatters import format_json, format_scan_result

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        client = GraphClient(token_provider=provider)
        service = ChannelService(graph_client=client)
        result = service.scan_activity(
            team_id=team_id,
            date=date,
            pages=pages,
            top=top,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(result)
        return

    format_scan_result(result)


@app.command("parse-url")
def parse_url_command(
    url: Annotated[
        str | None,
        typer.Argument(help="Teams URL to parse"),  # pyright: ignore[reportUnknownMemberType]
    ] = None,
) -> None:
    """Parse a Teams URL and extract IDs."""
    import sys

    from ms_teams_cli.domain.services import parse_teams_url

    if url is None:
        if sys.stdin.isatty():
            url = cast("str", typer.prompt("Teams URL"))
        else:
            typer.echo("Error: URL argument required when not in interactive mode", err=True)
            raise typer.Exit(code=1)

    assert isinstance(url, str)
    components = parse_teams_url(url)

    typer.echo(f"TEAM_ID    : {components.team_id or '(not found)'}")
    typer.echo(f"CHANNEL_ID : {components.channel_id or '(not found)'}")
    typer.echo(f"MESSAGE_ID : {components.message_id or '(not found)'}")
    typer.echo(f"TENANT_ID  : {components.tenant_id or '(not found)'}")

    if components.team_id:
        typer.echo()
        typer.echo(f"ms-teams channels --team {components.team_id}")
    if components.team_id and components.channel_id:
        typer.echo(
            f"ms-teams messages --team {components.team_id} --channel {components.channel_id}"
        )
    if components.team_id and components.channel_id and components.message_id:
        reply_command = (
            f"ms-teams replies --team {components.team_id} --channel {components.channel_id} "
            f"--thread {components.message_id}"
        )
        typer.echo(reply_command)


@app.command("token")
def token_command() -> None:
    """Force token renewal and show expiry."""
    from ms_teams_cli.domain.exceptions import TeamsError
    from ms_teams_cli.infrastructure.az_provider import AzGraphTokenProvider
    from ms_teams_cli.infrastructure.token_cache import TokenCache

    try:
        cache = TokenCache()
        provider = AzGraphTokenProvider(cache=cache)
        _ = provider.renew()
        cached = cache.load()
        if cached is None:
            typer.echo("Error: Token cache is empty after renewal", err=True)
            raise typer.Exit(code=1)

        data = cache.path.read_text(encoding="utf-8")
        token_data = cast("dict[str, object]", json.loads(data))
        expires_on = token_data.get("expiresOn", "")
        expiry_str = expires_on or "(unknown)"

        typer.echo(f"Token OK, expires: {expiry_str}")
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


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
    from ms_teams_cli.application.chats import ChatService
    from ms_teams_cli.domain.entities import ChatType
    from ms_teams_cli.infrastructure.az_provider import AzChatTokenProvider
    from ms_teams_cli.infrastructure.chat_client import ChatServiceClient
    from ms_teams_cli.infrastructure.token_cache import ChatTokenCache
    from ms_teams_cli.presentation.formatters import format_chats_table, format_json

    resolved_type: ChatType | None = None
    if chat_type is not None:
        try:
            resolved_type = ChatType(chat_type)
        except ValueError as exc:
            typer.echo(f"Invalid chat type: {chat_type}", err=True)
            raise typer.Exit(code=1) from exc

    try:
        cache = ChatTokenCache()
        provider = AzChatTokenProvider(cache=cache)
        client = ChatServiceClient(token_provider=provider)
        service = ChatService(chat_client=client)
        chats = service.list_chats(top=top, chat_type=resolved_type)
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
    from ms_teams_cli.application.chats import ChatService
    from ms_teams_cli.domain.entities import ChatType
    from ms_teams_cli.infrastructure.az_provider import AzChatTokenProvider
    from ms_teams_cli.infrastructure.chat_client import ChatServiceClient
    from ms_teams_cli.infrastructure.token_cache import ChatTokenCache
    from ms_teams_cli.presentation.formatters import format_json, format_unread_table

    resolved_type: ChatType | None = None
    if chat_type is not None:
        try:
            resolved_type = ChatType(chat_type)
        except ValueError as exc:
            typer.echo(f"Invalid chat type: {chat_type}", err=True)
            raise typer.Exit(code=1) from exc

    try:
        cache = ChatTokenCache()
        provider = AzChatTokenProvider(cache=cache)
        client = ChatServiceClient(token_provider=provider)
        service = ChatService(chat_client=client)
        chats = service.list_unread(chat_type=resolved_type)
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
    from ms_teams_cli.application.chats import ChatService
    from ms_teams_cli.infrastructure.az_provider import AzChatTokenProvider
    from ms_teams_cli.infrastructure.chat_client import ChatServiceClient
    from ms_teams_cli.infrastructure.token_cache import ChatTokenCache
    from ms_teams_cli.presentation.formatters import format_chat_messages_table, format_json

    try:
        cache = ChatTokenCache()
        provider = AzChatTokenProvider(cache=cache)
        client = ChatServiceClient(token_provider=provider)
        service = ChatService(chat_client=client)
        messages = service.get_messages(chat_id=chat_id, top=top)
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
    from ms_teams_cli.application.chats import ChatService
    from ms_teams_cli.infrastructure.az_provider import AzChatTokenProvider
    from ms_teams_cli.infrastructure.chat_client import ChatServiceClient
    from ms_teams_cli.infrastructure.token_cache import ChatTokenCache

    try:
        cache = ChatTokenCache()
        provider = AzChatTokenProvider(cache=cache)
        client = ChatServiceClient(token_provider=provider)
        service = ChatService(chat_client=client)
        chat_name = service.resolve_chat_name(chat_id)
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
        msg_id = service.send_message(chat_id, message)
        typer.echo(f"Message sent. (id: {msg_id})")
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
