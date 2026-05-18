from __future__ import annotations

from typing import TYPE_CHECKING

from ms_teams_cli.application.use_cases.channels import GetMessagesUseCase
from ms_teams_cli.domain.entities import ChannelMessage, MessageAuthor, MessageBody

if TYPE_CHECKING:
    from collections.abc import Iterator


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
    def get_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 20,
        pages: int = 1,
        since: str | None = None,
    ) -> Iterator[ChannelMessage]:
        return iter([_msg("m1"), _msg("m2", "Bob")])


def test_get_messages_returns_messages() -> None:
    use_case = GetMessagesUseCase(repo=FakeChannelRepo())  # type: ignore[arg-type]
    messages = list(use_case.execute(team_id="t1", channel_id="c1"))
    assert len(messages) == 2
    assert messages[0].id == "m1"


def test_get_messages_passes_params() -> None:
    class CapturingRepo:
        captured: dict[str, object] = {}

        def get_messages(
            self,
            team_id: str,
            channel_id: str,
            top: int = 20,
            pages: int = 1,
            since: str | None = None,
        ) -> Iterator[ChannelMessage]:
            self.captured = {
                "team_id": team_id,
                "channel_id": channel_id,
                "top": top,
                "pages": pages,
                "since": since,
            }
            return iter([])

    repo = CapturingRepo()
    use_case = GetMessagesUseCase(repo=repo)  # type: ignore[arg-type]
    list(use_case.execute(
        team_id="t1", channel_id="c1", top=10, pages=3, since="2024-01-01T00:00:00Z",
    ))
    assert repo.captured == {
        "team_id": "t1",
        "channel_id": "c1",
        "top": 10,
        "pages": 3,
        "since": "2024-01-01T00:00:00Z",
    }
