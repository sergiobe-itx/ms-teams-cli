from __future__ import annotations

from ms_teams_cli.application.use_cases.channels import GetThreadUseCase
from ms_teams_cli.domain.entities import ChannelMessage, MessageAuthor, MessageBody


def _msg(msg_id: str, author: str = "Alice") -> ChannelMessage:
    return ChannelMessage(
        id=msg_id,
        createdDateTime="2024-01-15T14:30:00Z",
        author=MessageAuthor(displayName=author),
        body=MessageBody(content="<p>Hello</p>", contentType="html"),
        replyCount=0,
        messageType="message",
        replyToId=None,
    )


class FakeChannelRepo:
    def get_thread(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        top: int = 50,
    ) -> tuple[ChannelMessage, list[ChannelMessage]]:
        return _msg("parent"), [_msg("r1", "Bob"), _msg("r2", "Carol")]


def test_get_thread_returns_parent_and_replies() -> None:
    use_case = GetThreadUseCase(repo=FakeChannelRepo())  # type: ignore[arg-type]
    parent, replies = use_case.execute(team_id="t1", channel_id="c1", message_id="m1")
    assert parent.id == "parent"
    assert len(replies) == 2
    assert replies[0].author.display_name == "Bob"


def test_get_thread_passes_params() -> None:
    class CapturingRepo:
        captured: dict[str, object] = {}

        def get_thread(
            self,
            team_id: str,
            channel_id: str,
            message_id: str,
            top: int = 50,
        ) -> tuple[ChannelMessage, list[ChannelMessage]]:
            self.captured = {
                "team_id": team_id,
                "channel_id": channel_id,
                "message_id": message_id,
                "top": top,
            }
            return _msg("p"), []

    repo = CapturingRepo()
    use_case = GetThreadUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(team_id="t1", channel_id="c1", message_id="m99", top=25)
    assert repo.captured == {
        "team_id": "t1",
        "channel_id": "c1",
        "message_id": "m99",
        "top": 25,
    }
