"""Tests for URL parser."""
from __future__ import annotations

from ms_teams_cli.domain.url_parser import TeamsUrlComponents, parse_teams_url


def test_parse_message_url_all_components() -> None:
    """Full URL with /l/message/, groupId, tenantId → all 4 fields extracted."""
    url = "https://teams.microsoft.com/l/message/19%3Axyz%40thread.tacv2/1234567890?groupId=abc123&tenantId=tenant456"
    result = parse_teams_url(url)
    assert result.team_id == "abc123"
    assert result.channel_id == "19:xyz@thread.tacv2"
    assert result.message_id == "1234567890"
    assert result.tenant_id == "tenant456"


def test_parse_message_url_url_encoded() -> None:
    """URL-encoded channel ID (e.g. 19%3Axyz%40thread.tacv2) → decoded correctly."""
    url = "https://teams.microsoft.com/l/message/19%3Axyz%40thread.tacv2/9876543210"
    result = parse_teams_url(url)
    assert result.channel_id == "19:xyz@thread.tacv2"
    assert result.message_id == "9876543210"


def test_parse_channel_url() -> None:
    """URL with /l/channel/ only (no message) → channel_id extracted, message_id=''."""
    url = "https://teams.microsoft.com/l/channel/19%3Axyz%40thread.tacv2?groupId=abc123"
    result = parse_teams_url(url)
    assert result.team_id == "abc123"
    assert result.channel_id == "19:xyz@thread.tacv2"
    assert result.message_id == ""


def test_parse_team_url() -> None:
    """URL with /l/team/ → channel_id extracted from team path."""
    url = "https://teams.microsoft.com/l/team/abc123"
    result = parse_teams_url(url)
    assert result.channel_id == "abc123"


def test_parse_url_no_match() -> None:
    """Plain URL with no Teams path → all fields empty string."""
    url = "https://teams.microsoft.com/"
    result = parse_teams_url(url)
    assert result.team_id == ""
    assert result.channel_id == ""
    assert result.message_id == ""
    assert result.tenant_id == ""


def test_parse_url_query_params_only() -> None:
    """URL with only groupId and tenantId params → team_id and tenant_id extracted."""
    url = "https://teams.microsoft.com/?groupId=team123&tenantId=tenant789"
    result = parse_teams_url(url)
    assert result.team_id == "team123"
    assert result.tenant_id == "tenant789"
    assert result.channel_id == ""
    assert result.message_id == ""


def test_parse_url_empty_string() -> None:
    """parse_teams_url('') → TeamsUrlComponents() with all empty."""
    result = parse_teams_url("")
    assert result.team_id == ""
    assert result.channel_id == ""
    assert result.message_id == ""
    assert result.tenant_id == ""


def test_parse_url_returns_teams_url_components() -> None:
    """Return type is TeamsUrlComponents."""
    result = parse_teams_url("https://teams.microsoft.com/")
    assert isinstance(result, TeamsUrlComponents)
