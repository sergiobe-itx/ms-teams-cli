from __future__ import annotations

from ms_teams_cli.application.use_cases.channels import FindUnansweredUseCase
from ms_teams_cli.domain.entities import ChannelMessage, MessageAuthor, MessageBody


def _msg(msg_id: str) -> ChannelMessage:
    return ChannelMessage(
        id=msg_id,
        createdDateTime="2024-01-15T14:30:00Z",
        author=MessageAuthor(displayName="Alice"),
        body=MessageBody(content="<p>Hello</p>", contentType="html"),
        replyCount=0,
        messageType="message",
        replyToId=None,
    )


class FakeChannelRepo:
    def find_unanswered(
        self,
        team_id: str,
        channel_id: str,
        minutes: int = 120,
    ) -> list[ChannelMessage]:
        return [_msg("u1"), _msg("u2")]


def test_find_unanswered_returns_messages() -> None:
    use_case = FindUnansweredUseCase(repo=FakeChannelRepo())  # type: ignore[arg-type]
    result = use_case.execute(team_id="t1", channel_id="c1")
    assert len(result) == 2
    assert result[0].id == "u1"


def test_find_unanswered_passes_minutes() -> None:
    class CapturingRepo:
        captured_minutes: int = 0

        def find_unanswered(
            self,
            team_id: str,
            channel_id: str,
            minutes: int = 120,
        ) -> list[ChannelMessage]:
            self.captured_minutes = minutes
            return []

    repo = CapturingRepo()
    use_case = FindUnansweredUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(team_id="t1", channel_id="c1", minutes=60)
    assert repo.captured_minutes == 60
