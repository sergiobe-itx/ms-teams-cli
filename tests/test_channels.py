"""Tests for channel application service and teams CLI."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from typer.testing import CliRunner

import ms_teams_cli.application.channels as channels_module
import ms_teams_cli.infrastructure.az_provider as az_provider_module
import ms_teams_cli.infrastructure.graph_client as graph_client_module
import ms_teams_cli.infrastructure.token_cache as token_cache_module
import ms_teams_cli.presentation.cli as cli_module
import ms_teams_cli.presentation.formatters as formatters_module
from ms_teams_cli.application.channels import ChannelService
from ms_teams_cli.domain.models import Channel, Team

if TYPE_CHECKING:
    import pytest

    from ms_teams_cli.infrastructure.graph_client import GraphClient


app = cli_module.app
runner = CliRunner()


class FakeGraphClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload: dict[str, object] = payload
        self.called_urls: list[str] = []

    def get(self, url: str) -> dict[str, object]:
        self.called_urls.append(url)
        return self._payload


class FakeTokenCache:
    def __init__(self) -> None:
        pass


class FakeTokenProvider:
    def __init__(self, cache: FakeTokenCache | None = None) -> None:
        self.cache: FakeTokenCache | None = cache


class FakeGraphClientFactory:
    def __init__(self, token_provider: FakeTokenProvider) -> None:
        self.token_provider: FakeTokenProvider = token_provider


class FakeChannelService:
    teams: list[Team] = []
    channels: list[Channel] = []

    def __init__(self, graph_client: FakeGraphClientFactory) -> None:
        self.graph_client: FakeGraphClientFactory = graph_client

    def list_teams(self) -> list[Team]:
        return self.teams

    def list_channels(self, team_id: str) -> list[Channel]:
        return self.channels


def test_list_teams_returns_team_objects() -> None:
    client = FakeGraphClient(
        {
            "value": [
                {"id": "t1", "displayName": "Team A", "description": "desc"},
                {"id": "t2", "displayName": "Team B", "description": None},
            ]
        }
    )

    teams = ChannelService(graph_client=cast("GraphClient", cast("object", client))).list_teams()

    assert teams == [
        Team(id="t1", displayName="Team A", description="desc"),
        Team(id="t2", displayName="Team B", description=None),
    ]


def test_list_teams_empty() -> None:
    client = FakeGraphClient({"value": []})

    teams = ChannelService(graph_client=cast("GraphClient", cast("object", client))).list_teams()

    assert teams == []


def test_list_channels_returns_channel_objects() -> None:
    client = FakeGraphClient(
        {
            "value": [
                {"id": "c1", "displayName": "General", "description": "main"},
                {"id": "c2", "displayName": "Random", "description": None},
            ]
        }
    )

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    channels = service.list_channels("team-123")

    assert channels == [
        Channel(id="c1", displayName="General", description="main"),
        Channel(id="c2", displayName="Random", description=None),
    ]


def test_list_channels_empty() -> None:
    client = FakeGraphClient({"value": []})

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    channels = service.list_channels("team-123")

    assert channels == []


def test_list_channels_uses_correct_url() -> None:
    client = FakeGraphClient({"value": []})

    service = ChannelService(graph_client=cast("GraphClient", cast("object", client)))
    service.list_channels("team-id-123")

    assert len(client.called_urls) == 1
    assert "team-id-123" in client.called_urls[0]
    assert "channels" in client.called_urls[0]


def test_teams_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    teams = [
        Team(id="t1", displayName="Team A", description="desc"),
        Team(id="t2", displayName="Team B", description=None),
    ]
    FakeChannelService.teams = teams

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[list[Team]] = []

    def fake_formatter(items: list[Team]) -> None:
        captured.append(items)
        for item in items:
            print(item.display_name)
        print(f"{len(items)} teams.")

    monkeypatch.setattr(formatters_module, "format_teams_table", fake_formatter)

    result = runner.invoke(app, ["teams"])

    assert result.exit_code == 0
    assert captured == [teams]
    assert "Team A" in result.stdout
    assert "Team B" in result.stdout
    assert "2 teams." in result.stdout


def test_teams_cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    teams = [Team(id="t1", displayName="Team A", description="desc")]
    FakeChannelService.teams = teams

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        item = cast("list[Team]", data)[0]
        print(json.dumps(item.model_dump(by_alias=False)))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["teams", "--json"])

    assert result.exit_code == 0
    assert captured == [teams]
    assert json.loads(result.stdout) == {
        "id": "t1",
        "display_name": "Team A",
        "description": "desc",
    }


def test_channels_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    channels = [
        Channel(id="c1", displayName="General", description="main"),
        Channel(id="c2", displayName="Random", description=None),
    ]
    FakeChannelService.channels = channels

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[list[Channel]] = []

    def fake_formatter(items: list[Channel]) -> None:
        captured.append(items)
        for item in items:
            print(item.display_name)
        print(f"{len(items)} channels.")

    monkeypatch.setattr(formatters_module, "format_channels_table", fake_formatter)

    result = runner.invoke(app, ["channels", "--team", "t1"])

    assert result.exit_code == 0
    assert captured == [channels]
    assert "General" in result.stdout
    assert "Random" in result.stdout
    assert "2 channels." in result.stdout


def test_channels_cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    channels = [Channel(id="c1", displayName="General", description="main")]
    FakeChannelService.channels = channels

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeTokenProvider)
    monkeypatch.setattr(graph_client_module, "GraphClient", FakeGraphClientFactory)
    monkeypatch.setattr(channels_module, "ChannelService", FakeChannelService)

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        item = cast("list[Channel]", data)[0]
        print(json.dumps(item.model_dump(by_alias=False)))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["channels", "--team", "t1", "--json"])

    assert result.exit_code == 0
    assert captured == [channels]
    assert json.loads(result.stdout) == {
        "id": "c1",
        "display_name": "General",
        "description": "main",
    }
