"""Scan activity use case."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms_teams_cli.domain.entities import ScanResult
    from ms_teams_cli.domain.ports import ChannelRepository


class ScanActivityUseCase:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    def execute(
        self,
        team_id: str,
        date: str,
        pages: int = 2,
        top: int = 50,
    ) -> ScanResult:
        return self._repo.scan_activity(
            team_id=team_id,
            date=date,
            pages=pages,
            top=top,
        )
