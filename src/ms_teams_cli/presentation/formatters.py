"""Output formatters for ms-teams-cli."""
from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from ms_teams_cli.domain.models import Team


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
