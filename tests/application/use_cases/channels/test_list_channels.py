from __future__ import annotations

from ms_teams_cli.application.use_cases.channels import ListChannelsUseCase
from ms_teams_cli.domain.entities import Channel


class FakeChannelRepo:
    def list_channels(self, team_id: str) -> list[Channel]:
        return [
            Channel(id="c1", displayName="General", description="main"),
            Channel(id="c2", displayName="Random", description=None),
        ]


def test_list_channels_returns_channel_objects() -> None:
    use_case = ListChannelsUseCase(repo=FakeChannelRepo())  # type: ignore[arg-type]
    channels = use_case.execute(team_id="t1")
    assert len(channels) == 2
    assert channels[0].display_name == "General"


def test_list_channels_passes_team_id() -> None:
    class CapturingRepo:
        captured_team_id: str = ""

        def list_channels(self, team_id: str) -> list[Channel]:
            self.captured_team_id = team_id
            return []

    repo = CapturingRepo()
    use_case = ListChannelsUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(team_id="team-xyz")
    assert repo.captured_team_id == "team-xyz"
