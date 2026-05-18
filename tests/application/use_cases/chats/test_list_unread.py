from __future__ import annotations

from ms_teams_cli.application.use_cases.chats import ListUnreadUseCase
from ms_teams_cli.domain.entities import Chat, ChatType


class FakeChatRepo:
    def list_unread(self, chat_type: ChatType | None = None) -> list[Chat]:
        chats = [
            Chat(id="c1", chat_type=ChatType.GROUP, display_name="Unread Group"),
            Chat(id="c2", chat_type=ChatType.ONE_TO_ONE, display_name="Chat with Bob"),
        ]
        if chat_type:
            return [c for c in chats if c.chat_type == chat_type]
        return chats


def test_list_unread_returns_chats() -> None:
    use_case = ListUnreadUseCase(repo=FakeChatRepo())  # type: ignore[arg-type]
    chats = use_case.execute()
    assert len(chats) == 2


def test_list_unread_filters_by_type() -> None:
    use_case = ListUnreadUseCase(repo=FakeChatRepo())  # type: ignore[arg-type]
    chats = use_case.execute(chat_type=ChatType.ONE_TO_ONE)
    assert len(chats) == 1
    assert chats[0].display_name == "Chat with Bob"
