"""Output formatters for ms-teams-cli."""
from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ms_teams_cli.domain.entities import (
        CalendarEvent,
        Channel,
        ChannelMessage,
        Chat,
        ChatMessage,
        ScanResult,
        Team,
    )


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
        _print_empty_result("No teams found.")
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
        _print_empty_result("No channels found.")
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


def _print_empty_result(message: str = "No results found.") -> None:
    print(message)


def format_messages_table(messages: Iterable[ChannelMessage]) -> None:
    """Print channel messages as a table (TTY) or plain text (non-TTY)."""
    from ms_teams_cli.domain.services import format_datetime, strip_html

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
        _print_empty_result("No messages found.")
        return
    print(f"\n{count} messages.")


def format_thread(parent: ChannelMessage, replies: list[ChannelMessage]) -> None:
    """Display an original post with all its replies."""
    from ms_teams_cli.domain.services import format_datetime, strip_html

    print("── ORIGINAL POST " + "─" * 44)
    print(f"From : {parent.author.display_name}")
    print(f"Date : {format_datetime(parent.created_date_time)}")
    print(f"Body : {strip_html(parent.body.content)[:300]}")
    print()
    print(f"── REPLIES ({len(replies)} total) " + "─" * 40)
    if not replies:
        _print_empty_result("No replies found.")
    for i, msg in enumerate(replies, 1):
        print(f"[{i}] {msg.author.display_name} @ {format_datetime(msg.created_date_time)}")
        print(f"    {strip_html(msg.body.content)[:200]}")
        print()
    print(f"{len(replies)} replies.")


def format_unanswered_table(messages: list[ChannelMessage], minutes: int) -> None:
    """Print unanswered messages as table."""
    from ms_teams_cli.domain.services import format_datetime, strip_html

    if not messages:
        _print_empty_result(f"No unanswered posts in last {minutes} min.")
        return

    if _is_tty():
        console = Console()
        table = Table(
            title=f"Unanswered posts (last {minutes} min)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Author", style="green", min_width=20)
        table.add_column("When", style="dim", min_width=16)
        table.add_column("Preview")
        for msg in messages:
            preview = strip_html(msg.body.content)[:60]
            table.add_row(
                msg.author.display_name,
                format_datetime(msg.created_date_time),
                preview,
            )
        console.print(table)
    else:
        print(f"Posts without replies in last {minutes} min:")
        print(f"{'AUTHOR':<25} {'WHEN':<20} PREVIEW")
        print("-" * 90)
        for msg in messages:
            preview = strip_html(msg.body.content)[:60]
            row = (
                f"{msg.author.display_name:<25} "
                f"{format_datetime(msg.created_date_time):<20} {preview}"
            )
            print(row)
    print(f"\n{len(messages)} unanswered posts (window: last {minutes} min).")


def format_scan_result(result: ScanResult) -> None:
    """Print scan activity results with per-channel thread summaries."""
    from ms_teams_cli.domain.services import format_datetime, strip_html

    if not result.channels:
        _print_empty_result(f"No activity found on {result.date}.")
        return

    total_posts = 0
    total_replies = 0

    for ch in result.channels:
        day_posts = sum(1 for t in ch.threads if t.root_created_on_date)
        day_reps = sum(len(t.replies_on_date) for t in ch.threads)
        total_posts += day_posts
        total_replies += day_reps

        print("━" * 64)
        print(f"  {ch.channel_name}  [{day_posts} posts | {day_reps} replies]")
        print("━" * 64)

        for t in ch.threads:
            root_dt = format_datetime(t.root_message.created_date_time)
            tag = " ◀ TODAY" if t.root_created_on_date else f"  (thread from {root_dt[:10]})"
            print(f"  ▶ [{root_dt}]{tag}")
            body = strip_html(t.root_message.body.content)[:120]
            print(f"     {t.root_message.author.display_name}: {body}")
            for r in t.replies_on_date:
                r_time = r.created_date_time[11:16] if len(r.created_date_time) > 16 else ""
                r_body = strip_html(r.body.content)[:100]
                print(f"    ↩ {r_time}  {r.author.display_name:<28} {r_body}")
            print()

    print("=" * 64)
    print(f"TOTAL {result.date}: {total_posts} new posts | {total_replies} replies")
    print(f"Active channels: {len(result.channels)}")


def format_chats_table(chats: list[Chat]) -> None:
    """Print chats as table."""
    from ms_teams_cli.domain.services import format_datetime

    if not chats:
        _print_empty_result("No chats found.")
        return

    if _is_tty():
        console = Console()
        table = Table(title="Chats", show_header=True, header_style="bold cyan")
        table.add_column("Type", style="magenta", min_width=10)
        table.add_column("Name", style="green", min_width=30)
        table.add_column("Last message", style="dim", min_width=16)
        table.add_column("Preview")
        for chat in chats:
            table.add_row(
                chat.chat_type.value,
                chat.display_name,
                format_datetime(chat.last_message_time or ""),
                chat.last_message_preview or "",
            )
        console.print(table)
    else:
        print(f"{'TYPE':<10} {'NAME':<50} {'LAST MESSAGE':<20} PREVIEW")
        print("-" * 120)
        for chat in chats:
            row = (
                f"{chat.chat_type.value:<10} {chat.display_name[:48]:<50} "
                f"{format_datetime(chat.last_message_time or ''):<20} "
                f"{(chat.last_message_preview or '')[:50]}"
            )
            print(row)
    print(f"\n{len(chats)} conversations.")


def format_unread_table(chats: list[Chat]) -> None:
    """Print unread chats as table."""
    from ms_teams_cli.domain.services import format_datetime

    if not chats:
        _print_empty_result("No unread chats.")
        return

    if _is_tty():
        console = Console()
        table = Table(title="Unread Chats", show_header=True, header_style="bold cyan")
        table.add_column("Type", style="magenta", min_width=10)
        table.add_column("Name", style="green", min_width=30)
        table.add_column("Last message", style="dim", min_width=16)
        table.add_column("Preview")
        for chat in chats:
            table.add_row(
                chat.chat_type.value,
                chat.display_name,
                format_datetime(chat.last_message_time or ""),
                chat.last_message_preview or "",
            )
        console.print(table)
    else:
        print(f"{'TYPE':<10} {'NAME':<50} {'LAST MESSAGE':<20} PREVIEW")
        print("-" * 120)
        for chat in chats:
            row = (
                f"{chat.chat_type.value:<10} {chat.display_name[:48]:<50} "
                f"{format_datetime(chat.last_message_time or ''):<20} "
                f"{(chat.last_message_preview or '')[:50]}"
            )
            print(row)
    print(f"\n{len(chats)} unread conversations.")


def format_chat_messages_table(messages: list[ChatMessage]) -> None:
    """Print chat messages as table."""
    from ms_teams_cli.domain.services import format_datetime, strip_html

    if not messages:
        _print_empty_result("No messages found.")
        return

    if _is_tty():
        console = Console()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("When", style="dim", min_width=16)
        table.add_column("From", style="green", min_width=20)
        table.add_column("Message")
        for msg in messages:
            preview = strip_html(msg.content)[:100]
            table.add_row(
                format_datetime(msg.compose_time),
                msg.sender_name,
                preview,
            )
        console.print(table)
    else:
        print(f"{'WHEN':<20} {'FROM':<25} MESSAGE")
        print("-" * 100)
        for msg in messages:
            preview = strip_html(msg.content)[:80]
            row = f"{format_datetime(msg.compose_time):<20} {msg.sender_name:<25} {preview}"
            print(row)
    print(f"\n{len(messages)} messages.")


def _format_duration(start_dt: str, end_dt: str) -> str:
    """Return compact duration string: '45m', '1h30m', '2h', etc."""
    try:
        from datetime import datetime

        def _parse(s: str) -> datetime:
            s = s[:26]  # trim to microsecond precision
            for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(s, f)  # noqa: DTZ007
                except ValueError:
                    continue
            return datetime.min  # noqa: DTZ007

        delta = _parse(end_dt) - _parse(start_dt)
        total_minutes = int(delta.total_seconds() // 60)
        if total_minutes <= 0:
            return "—"
        h, m = divmod(total_minutes, 60)
        if h == 0:
            return f"{m}m"
        if m == 0:
            return f"{h}h"
        return f"{h}h{m}m"
    except Exception:  # noqa: BLE001
        return "—"


def format_calendar_table(events: list[CalendarEvent]) -> None:
    """Print calendar events as Rich table on TTY and plain text otherwise."""
    if not events:
        _print_empty_result("No events found in this date range.")
        return

    if _is_tty():
        console = Console()
        table = Table(title="Calendar Events", show_header=True, header_style="bold cyan")
        table.add_column("DATE", style="dim", min_width=10)
        table.add_column("TIME", style="green", min_width=11)
        table.add_column("DURATION", justify="right", min_width=8)
        table.add_column("SUBJECT")
        table.add_column("ORGANIZER", style="dim", min_width=20)
        for ev in events:
            date_str = ev.start_datetime[:10] if ev.start_datetime else ""
            if ev.is_all_day:
                time_str = "All day"
                dur_str = "—"
            else:
                time_str = ev.start_datetime[11:16] if len(ev.start_datetime) > 16 else ""
                dur_str = _format_duration(ev.start_datetime, ev.end_datetime)
            table.add_row(date_str, time_str, dur_str, ev.subject, ev.organizer_name)
        console.print(table)
    else:
        print(f"{'DATE':<12} {'TIME':<11} {'DURATION':<9} {'SUBJECT':<50} ORGANIZER")
        print("-" * 110)
        for ev in events:
            date_str = ev.start_datetime[:10] if ev.start_datetime else ""
            if ev.is_all_day:
                time_str = "All day"
                dur_str = "—"
            else:
                time_str = ev.start_datetime[11:16] if len(ev.start_datetime) > 16 else ""
                dur_str = _format_duration(ev.start_datetime, ev.end_datetime)
            print(
                f"{date_str:<12} {time_str:<11} {dur_str:<9} "
                f"{ev.subject[:48]:<50} {ev.organizer_name}"
            )
    print(f"\n{len(events)} event(s) found.")
