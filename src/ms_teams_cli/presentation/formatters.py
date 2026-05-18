"""Output formatters for ms-teams-cli."""
from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ms_teams_cli.domain.models import Channel, ChannelMessage, Team


@runtime_checkable
class SupportsModelDump(Protocol):
    """Protocol for values that support Pydantic-style dumping."""

    def model_dump(self, *, by_alias: bool = False) -> dict[str, object]:
        """Dump object to a JSON-serializable dictionary."""
        ...


def _is_model_dump_sequence(data: object) -> bool:
    if not isinstance(data, list):
        return False
    items = cast("list[object]", data)
    return all(isinstance(item, SupportsModelDump) for item in items)


def _is_tty() -> bool:
    return sys.stdout.isatty()


def format_teams_table(teams: list[Team]) -> None:
    """Print teams as Rich table on TTY and plain text otherwise."""
    if not teams:
        print("No teams found.")
        return

    if _is_tty():
        console = Console()
        table = Table(title="Teams", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green", min_width=40)
        table.add_column("ID", style="dim", min_width=36)
        for team in teams:
            table.add_row(team.display_name, team.id)
        console.print(table)
    else:
        print(f"{'TEAM':<45} {'ID':<38}")
        print("-" * 84)
        for team in teams:
            print(f"{team.display_name:<45} {team.id:<38}")
    print(f"\n{len(teams)} teams.")


def format_channels_table(channels: list[Channel]) -> None:
    """Print channels as Rich table on TTY and plain text otherwise."""
    if not channels:
        print("No channels found.")
        return

    if _is_tty():
        console = Console()
        table = Table(title="Channels", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green", min_width=40)
        table.add_column("ID", style="dim", min_width=36)
        for channel in channels:
            table.add_row(channel.display_name, channel.id)
        console.print(table)
    else:
        print(f"{'CHANNEL':<45} {'ID':<60}")
        print("-" * 106)
        for channel in channels:
            print(f"{channel.display_name:<45} {channel.id:<60}")
    print(f"\n{len(channels)} channels.")


def format_json(data: object) -> None:
    """Serialize data to JSON, using Pydantic dumps when available."""
    if isinstance(data, SupportsModelDump):
        print(json.dumps(data.model_dump(by_alias=False), indent=2, ensure_ascii=False))
        return
    if _is_model_dump_sequence(data):
        items = cast("list[SupportsModelDump]", data)
        print(
            json.dumps(
                [item.model_dump(by_alias=False) for item in items],
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    print(json.dumps(data, indent=2, ensure_ascii=False))


def format_messages_table(messages: Iterable[ChannelMessage]) -> None:
    """Print channel messages as a table (TTY) or plain text (non-TTY)."""
    from ms_teams_cli.domain.text import format_datetime, strip_html

    count = 0
    if _is_tty():
        console = Console()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Author", style="green", min_width=20)
        table.add_column("When", style="dim", min_width=16)
        table.add_column("Replies", justify="right", min_width=7)
        table.add_column("Preview")
        for msg in messages:
            if msg.message_type != "message":
                continue
            rc = "(reply)" if msg.reply_to_id else str(msg.reply_count or "-")
            preview = strip_html(msg.body.content)[:80]
            table.add_row(
                msg.author.display_name,
                format_datetime(msg.created_date_time),
                rc,
                preview,
            )
            count += 1
        console.print(table)
    else:
        print(f"{'AUTHOR':<25} {'WHEN':<20} {'REPLIES':<8} SUBJECT / PREVIEW")
        print("-" * 100)
        for msg in messages:
            if msg.message_type != "message":
                continue
            rc = "(reply)" if msg.reply_to_id else str(msg.reply_count or "-")
            preview = strip_html(msg.body.content)[:80]
            row = (
                f"{msg.author.display_name:<25} "
                + f"{format_datetime(msg.created_date_time):<20} "
                + f"{rc:<8} {preview}"
            )
            print(row)
            count += 1
    if count == 0:
        print("No messages found.")
        return
    print(f"\n{count} messages.")


def format_thread(parent: ChannelMessage, replies: list[ChannelMessage]) -> None:
    """Display an original post with all its replies."""
    from ms_teams_cli.domain.text import format_datetime, strip_html

    print("── ORIGINAL POST " + "─" * 44)
    print(f"From : {parent.author.display_name}")
    print(f"Date : {format_datetime(parent.created_date_time)}")
    print(f"Body : {strip_html(parent.body.content)[:300]}")
    print()
    print(f"── REPLIES ({len(replies)} total) " + "─" * 40)
    if not replies:
        print("  (no replies)")
    for i, msg in enumerate(replies, 1):
        print(f"[{i}] {msg.author.display_name} @ {format_datetime(msg.created_date_time)}")
        print(f"    {strip_html(msg.body.content)[:200]}")
        print()
    print(f"{len(replies)} replies.")
