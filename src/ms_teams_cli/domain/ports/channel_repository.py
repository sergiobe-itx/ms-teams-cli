"""Channel repository protocol for ms-teams-cli."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ms_teams_cli.domain.entities import Channel, ChannelMessage, ScanResult, Team


class ChannelRepository(Protocol):
    """Protocol for channel data access."""

    def list_teams(self) -> list[Team]:
        """Return all teams the authenticated user is a member of."""
        ...

    def list_channels(self, team_id: str) -> list[Channel]:
        """Return all channels for the given team."""
        ...

    def get_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 20,
        pages: int = 1,
        since: str | None = None,
    ) -> Iterator[ChannelMessage]:
        """Yield messages from a channel, fetching up to `pages` pages of `top` items each."""
        ...

    def get_thread(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        top: int = 50,
    ) -> tuple[ChannelMessage, list[ChannelMessage]]:
        """Return the parent message and its replies for a thread."""
        ...

    def find_unanswered(
        self,
        team_id: str,
        channel_id: str,
        minutes: int = 120,
    ) -> list[ChannelMessage]:
        """Find messages with no replies within the last N minutes."""
        ...

    def scan_activity(
        self,
        team_id: str,
        date: str,
        pages: int = 2,
        top: int = 50,
    ) -> ScanResult:
        """Scan all channels of a team for activity on a specific date."""
        ...
