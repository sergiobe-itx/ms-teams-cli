"""Channel application services."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from ms_teams_cli.domain.models import (
    Channel,
    ChannelActivity,
    ChannelMessage,
    ScanResult,
    Team,
    ThreadActivity,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ms_teams_cli.infrastructure.graph_client import GraphClient


_GRAPH = "https://graph.microsoft.com/v1.0"
_GRAPH_BETA = "https://graph.microsoft.com/beta"
_TEAMS_URL = f"{_GRAPH}/me/joinedTeams?$select=id,displayName,description"
_CHANNELS_URL = "{_GRAPH}/teams/{team_id}/channels?$select=id,displayName,description"


def _as_team_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


def _as_channel_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


class ChannelService:
    """Application service for Microsoft Teams channel operations."""

    def __init__(self, graph_client: GraphClient) -> None:
        self._client: GraphClient = graph_client

    def list_teams(self) -> list[Team]:
        """Return all teams the authenticated user is a member of."""
        data = self._client.get(_TEAMS_URL)
        return [Team.model_validate(item) for item in _as_team_payloads(data.get("value", []))]

    def list_channels(self, team_id: str) -> list[Channel]:
        """Return all channels for the given team."""
        url = f"{_GRAPH}/teams/{team_id}/channels?$select=id,displayName,description"
        data = self._client.get(url)
        payloads = _as_channel_payloads(data.get("value", []))
        return [Channel.model_validate(item) for item in payloads]

    def get_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 20,
        pages: int = 1,
        since: str | None = None,
    ) -> Iterator[ChannelMessage]:
        """Yield messages from a channel, fetching up to `pages` pages of `top` items each."""
        url = f"{_GRAPH_BETA}/teams/{team_id}/channels/{channel_id}/messages?$top={top}"
        if since:
            url += f"&$filter=createdDateTime%20ge%20{since}"
        for item in self._client.paginate(url, max_pages=pages):
            yield ChannelMessage.model_validate(item)

    def get_thread(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        top: int = 50,
    ) -> tuple[ChannelMessage, list[ChannelMessage]]:
        """Return the parent message and its replies for a thread."""
        base = f"{_GRAPH_BETA}/teams/{team_id}/channels/{channel_id}/messages"
        parent_data = self._client.get(f"{base}/{message_id}")
        replies_data = self._client.get(f"{base}/{message_id}/replies?$top={top}")
        parent = ChannelMessage.model_validate(parent_data)
        replies = [
            ChannelMessage.model_validate(item)
            for item in _as_channel_payloads(replies_data.get("value", []))
        ]
        return parent, replies

    def find_unanswered(
        self,
        team_id: str,
        channel_id: str,
        minutes: int = 120,
    ) -> list[ChannelMessage]:
        """Find messages with no replies within the last N minutes."""
        url = f"{_GRAPH_BETA}/teams/{team_id}/channels/{channel_id}/messages?$top=50"
        data = self._client.get(url)
        msgs = _as_channel_payloads(data.get("value", []))
        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

        results: list[ChannelMessage] = []
        for m in msgs:
            if m.get("messageType") != "message":
                continue
            if m.get("replyToId"):
                continue
            if m.get("deletedDateTime"):
                continue
            reply_count = m.get("replyCount")
            if isinstance(reply_count, int) and reply_count > 0:
                continue
                continue
            created_str = m.get("createdDateTime")
            if not isinstance(created_str, str):
                continue
            try:
                created = datetime.fromisoformat(
                    re.sub(r"\.\d+", "", created_str).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                continue
            if created < cutoff:
                continue
            results.append(ChannelMessage.model_validate(m))
        return results

    def scan_activity(
        self,
        team_id: str,
        date: str,
        pages: int = 2,
        top: int = 50,
    ) -> ScanResult:
        """Scan all channels of a team for activity on a specific date."""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            raise ValueError("date must be YYYY-MM-DD")

        stop_before = (
            datetime.strptime(date, "%Y-%m-%d") - timedelta(days=3)
        ).strftime("%Y-%m-%d")

        ch_data = self._client.get(f"{_GRAPH}/teams/{team_id}/channels?$select=id,displayName")
        channels_raw = _as_channel_payloads(ch_data.get("value", []))

        channel_activities: list[ChannelActivity] = []

        for ch in channels_raw:
            cid = ch.get("id", "")
            cname = ch.get("displayName", "")
            if not isinstance(cid, str) or not isinstance(cname, str):
                continue

            msg_url = f"{_GRAPH_BETA}/teams/{team_id}/channels/{cid}/messages?$top={top}"
            msgs = list(self._client.paginate(msg_url, max_pages=pages, stop_before=stop_before))

            roots: dict[str, dict[str, object]] = {}
            for m in msgs:
                if m.get("messageType") != "message":
                    continue
                if m.get("deletedDateTime"):
                    continue
                if m.get("replyToId"):
                    continue
                created_dt = m.get("createdDateTime", "")
                if not isinstance(created_dt, str):
                    continue
                if created_dt[:10] >= stop_before:
                    roots[str(m.get("id", ""))] = m

            if not roots:
                continue

            channel_threads: list[ThreadActivity] = []
            for mid, root in sorted(
                roots.items(), key=lambda x: str(x[1].get("createdDateTime", ""))
            ):
                root_dt = str(root.get("createdDateTime", ""))
                root_on_day = root_dt.startswith(date)

                rep_url = (
                    f"{_GRAPH_BETA}/teams/{team_id}/channels/{cid}"
                    f"/messages/{mid}/replies?$top=50"
                )
                rep_data = self._client.get(rep_url)
                all_replies = _as_channel_payloads(rep_data.get("value", []))

                day_replies_raw = [
                    r
                    for r in all_replies
                    if isinstance(r.get("createdDateTime"), str)
                    and str(r.get("createdDateTime", "")).startswith(date)
                    and not r.get("deletedDateTime")
                ]

                if not root_on_day and not day_replies_raw:
                    continue

                day_replies = [ChannelMessage.model_validate(r) for r in day_replies_raw]
                root_message = ChannelMessage.model_validate(root)
                channel_threads.append(
                    ThreadActivity(
                        root_message=root_message,
                        replies_on_date=day_replies,
                        root_created_on_date=root_on_day,
                    )
                )

            if not channel_threads:
                continue

            channel_activities.append(
                ChannelActivity(
                    channel_name=cname,
                    channel_id=cid,
                    threads=channel_threads,
                )
            )

        return ScanResult(date=date, channels=channel_activities)
