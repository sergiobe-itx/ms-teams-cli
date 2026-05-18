from __future__ import annotations

from ms_teams_cli.application.use_cases.channels import ListTeamsUseCase
from ms_teams_cli.domain.entities import Team


class FakeChannelRepo:
    def list_teams(self) -> list[Team]:
        return [
            Team(id="t1", displayName="Alpha", description=None),
            Team(id="t2", displayName="Beta", description="Second team"),
        ]


def test_list_teams_returns_team_objects() -> None:
    use_case = ListTeamsUseCase(repo=FakeChannelRepo())  # type: ignore[arg-type]
    teams = use_case.execute()
    assert len(teams) == 2
    assert teams[0].display_name == "Alpha"
    assert teams[1].display_name == "Beta"


def test_list_teams_empty() -> None:
    class EmptyRepo:
        def list_teams(self) -> list[Team]:
            return []

    use_case = ListTeamsUseCase(repo=EmptyRepo())  # type: ignore[arg-type]
    assert use_case.execute() == []
