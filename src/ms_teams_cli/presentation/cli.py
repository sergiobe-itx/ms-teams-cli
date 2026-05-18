"""CLI entry point for ms-teams."""
from __future__ import annotations

from typing import Annotated

import typer

from ms_teams_cli.domain.exceptions import TeamsError

app = typer.Typer(
    name="ms-teams",
    help="Microsoft Teams CLI — read channels and chats.",
    no_args_is_help=True,
)


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


if __name__ == "__main__":
    app()
