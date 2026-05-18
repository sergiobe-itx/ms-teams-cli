"""URL parser for Microsoft Teams deep-links."""
from __future__ import annotations

import re
import urllib.parse
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class TeamsUrlComponents(BaseModel):
    """Extracted components from a Microsoft Teams deep-link URL."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    team_id: str = ""
    channel_id: str = ""
    message_id: str = ""
    tenant_id: str = ""


def parse_teams_url(url: str) -> TeamsUrlComponents:
    """Extract team_id, channel_id, message_id, tenant_id from a Teams URL.

    Handles /l/message/, /l/channel/, /l/team/ path patterns and
    groupId / tenantId query parameters.
    """
    parsed = urllib.parse.urlparse(url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    path = urllib.parse.unquote(parsed.path)

    team_id = params.get("groupId", "")
    tenant_id = params.get("tenantId", "")
    channel_id = ""
    message_id = ""

    m = re.search(r"/l/message/([^/]+)/([^/?]+)", path)
    if m:
        channel_id = urllib.parse.unquote(m.group(1))
        message_id = urllib.parse.unquote(m.group(2))

    if not channel_id:
        m = re.search(r"/l/channel/([^/]+)", path)
        if m:
            channel_id = urllib.parse.unquote(m.group(1))

    if not channel_id:
        m = re.search(r"/l/team/([^/]+)", path)
        if m:
            channel_id = urllib.parse.unquote(m.group(1))

    return TeamsUrlComponents(
        team_id=team_id,
        channel_id=channel_id,
        message_id=message_id,
        tenant_id=tenant_id,
    )
