from __future__ import annotations

from ms_teams_cli.application.use_cases.chats import GetChatMessagesUseCase
from ms_teams_cli.domain.entities import ChatMessage


class FakeChatRepo:
    def get_messages(self, chat_id: str, top: int = 30) -> list[ChatMessage]:
        return [
            ChatMessage(
                id="1", composetime="2024-01-01T00:00:00Z",
                imdisplayname="Alice", content="hi",
            ),
            ChatMessage(
                id="2", composetime="2024-01-02T00:00:00Z",
                imdisplayname="Bob", content="hello",
            ),
        ]


def test_get_chat_messages_returns_messages() -> None:
    use_case = GetChatMessagesUseCase(repo=FakeChatRepo())  # type: ignore[arg-type]
    messages = use_case.execute(chat_id="19:abc@thread.v2")
    assert len(messages) == 2
    assert messages[0].sender_name == "Alice"


def test_get_chat_messages_passes_top() -> None:
    class CapturingRepo:
        captured_top: int = 0

        def get_messages(self, chat_id: str, top: int = 30) -> list[ChatMessage]:
            self.captured_top = top
            return []

    repo = CapturingRepo()
    use_case = GetChatMessagesUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(chat_id="19:abc@thread.v2", top=10)
    assert repo.captured_top == 10
