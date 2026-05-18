"""CLI entry point for ms-teams."""
from __future__ import annotations

import typer

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


if __name__ == "__main__":
    app()
