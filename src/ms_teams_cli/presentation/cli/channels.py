"""Channel-related CLI commands."""
from __future__ import annotations

from typing import Annotated

import typer

from ms_teams_cli.domain.exceptions import TeamsError
from ms_teams_cli.presentation.cli._app import app


@app.command("teams")
def teams_command(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List all teams the user belongs to."""
    from ms_teams_cli.presentation.cli.formatters import format_json, format_teams_table
    from ms_teams_cli.presentation.dependencies import get_list_teams

    try:
        teams = get_list_teams().execute()
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
    from ms_teams_cli.presentation.cli.formatters import format_channels_table, format_json
    from ms_teams_cli.presentation.dependencies import get_list_channels

    try:
        channels = get_list_channels().execute(team_id)
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
    from ms_teams_cli.presentation.cli.formatters import format_json, format_messages_table
    from ms_teams_cli.presentation.dependencies import get_get_messages

    try:
        messages = get_get_messages().execute(
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
    from ms_teams_cli.presentation.cli.formatters import format_json, format_thread
    from ms_teams_cli.presentation.dependencies import get_get_thread

    try:
        parent, replies = get_get_thread().execute(
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
    from ms_teams_cli.presentation.cli.formatters import format_json, format_unanswered_table
    from ms_teams_cli.presentation.dependencies import get_find_unanswered

    try:
        messages = get_find_unanswered().execute(
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
    from ms_teams_cli.presentation.cli.formatters import format_json, format_scan_result
    from ms_teams_cli.presentation.dependencies import get_scan_activity

    try:
        result = get_scan_activity().execute(
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
