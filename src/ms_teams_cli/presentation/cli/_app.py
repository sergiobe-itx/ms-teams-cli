"""CLI app setup — Typer instance, error handling, and utility commands."""
from __future__ import annotations

import json
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
    from ms_teams_cli.infrastructure.auth import AzGraphTokenProvider, TokenCache

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

        from ms_teams_cli.infrastructure.auth.msal_provider import MsalGraphTokenProvider
        msal_provider = MsalGraphTokenProvider()
        try:
            msal_token = msal_provider.get_token()
            _ = msal_token
            typer.echo("MSAL: authenticated (silent renewal available)")
        except Exception:
            typer.echo("MSAL: not logged in (run: ms-teams login)")
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command("login")
def login_command() -> None:
    """Authenticate via MSAL device-code flow and cache the token."""
    from ms_teams_cli.domain.exceptions import TeamsError
    from ms_teams_cli.infrastructure.auth.msal_provider import MsalGraphTokenProvider

    try:
        provider = MsalGraphTokenProvider()
        _ = provider.login()
        typer.echo("Login successful. Token cached.")
    except TeamsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command("logout")
def logout_command() -> None:
    """Clear the MSAL token cache (sign out)."""
    from ms_teams_cli.infrastructure.auth.msal_provider import MsalGraphTokenProvider

    provider = MsalGraphTokenProvider()
    provider.logout()
    typer.echo("Logged out. MSAL cache cleared.")


# Register command submodules (triggers @app.command registration via import)
import ms_teams_cli.presentation.cli.calendar as _calendar  # noqa: E402, F401  # pyright: ignore[reportUnusedImport]
import ms_teams_cli.presentation.cli.channels as _channels  # noqa: E402, F401  # pyright: ignore[reportUnusedImport]
import ms_teams_cli.presentation.cli.chats as _chats  # noqa: E402, F401  # pyright: ignore[reportUnusedImport]
