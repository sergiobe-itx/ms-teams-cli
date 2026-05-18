"""Calendar CLI commands."""
from __future__ import annotations

import re
from typing import Annotated

import typer

from ms_teams_cli.domain.exceptions import TeamsError
from ms_teams_cli.presentation.cli._app import app


@app.command("calendar")
def calendar_command(
    from_date: Annotated[
        str,
        typer.Option("--from", help="Start date YYYY-MM-DD (inclusive)"),  # pyright: ignore[reportUnknownMemberType]
    ],
    to_date: Annotated[
        str,
        typer.Option("--to", help="End date YYYY-MM-DD (inclusive)"),  # pyright: ignore[reportUnknownMemberType]
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),  # pyright: ignore[reportUnknownMemberType]
    ] = False,
) -> None:
    """List calendar events in a date range."""
    from ms_teams_cli.presentation.cli.formatters import format_calendar_table, format_json
    from ms_teams_cli.presentation.dependencies import get_list_calendar_events

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not date_re.match(from_date):
        typer.echo("Error: --from must be YYYY-MM-DD", err=True)
        raise typer.Exit(code=1)
    if not date_re.match(to_date):
        typer.echo("Error: --to must be YYYY-MM-DD", err=True)
        raise typer.Exit(code=1)
    if from_date > to_date:
        typer.echo("Error: --from must be \u2264 --to", err=True)
        raise typer.Exit(code=1)

    try:
        events = get_list_calendar_events().execute(from_date, to_date)
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        format_json(events)
        return

    format_calendar_table(events)
