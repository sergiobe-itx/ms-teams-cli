from __future__ import annotations

from ms_teams_cli.application.use_cases.channels import ScanActivityUseCase
from ms_teams_cli.domain.entities import ScanResult


class FakeChannelRepo:
    def scan_activity(
        self,
        team_id: str,
        date: str,
        pages: int = 2,
        top: int = 50,
    ) -> ScanResult:
        return ScanResult(date=date, channels=[])


def test_scan_activity_returns_scan_result() -> None:
    use_case = ScanActivityUseCase(repo=FakeChannelRepo())  # type: ignore[arg-type]
    result = use_case.execute(team_id="t1", date="2024-06-15")
    assert result.date == "2024-06-15"
    assert result.channels == []


def test_scan_activity_passes_params() -> None:
    class CapturingRepo:
        captured: dict[str, object] = {}

        def scan_activity(
            self,
            team_id: str,
            date: str,
            pages: int = 2,
            top: int = 50,
        ) -> ScanResult:
            self.captured = {
                "team_id": team_id,
                "date": date,
                "pages": pages,
                "top": top,
            }
            return ScanResult(date=date, channels=[])

    repo = CapturingRepo()
    use_case = ScanActivityUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(team_id="t1", date="2024-01-01", pages=5, top=100)
    assert repo.captured == {
        "team_id": "t1",
        "date": "2024-01-01",
        "pages": 5,
        "top": 100,
    }
