from __future__ import annotations

from ms_teams_cli.application.use_cases.chats import ResolveChatNameUseCase, SendMessageUseCase


class FakeChatRepo:
    def send_message(self, chat_id: str, message: str) -> str:
        return "msg-42"

    def resolve_chat_name(self, chat_id: str) -> str:
        return "Architecture"


def test_send_message_returns_id() -> None:
    use_case = SendMessageUseCase(repo=FakeChatRepo())  # type: ignore[arg-type]
    result = use_case.execute(chat_id="19:abc@thread.v2", message="Hello")
    assert result == "msg-42"


def test_send_message_passes_params() -> None:
    class CapturingRepo:
        captured_chat_id: str = ""
        captured_message: str = ""

        def send_message(self, chat_id: str, message: str) -> str:
            self.captured_chat_id = chat_id
            self.captured_message = message
            return "ok"

    repo = CapturingRepo()
    use_case = SendMessageUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(chat_id="19:target@thread.v2", message="Test msg")
    assert repo.captured_chat_id == "19:target@thread.v2"
    assert repo.captured_message == "🤖 Test msg"


def test_send_message_adds_robot_prefix() -> None:
    class CapturingRepo:
        captured_message: str = ""

        def send_message(self, chat_id: str, message: str) -> str:
            self.captured_message = message
            return "ok"

    repo = CapturingRepo()
    use_case = SendMessageUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(chat_id="19:target@thread.v2", message="Hello world")
    assert repo.captured_message == "🤖 Hello world"


def test_send_message_does_not_double_prefix() -> None:
    class CapturingRepo:
        captured_message: str = ""

        def send_message(self, chat_id: str, message: str) -> str:
            self.captured_message = message
            return "ok"

    repo = CapturingRepo()
    use_case = SendMessageUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(chat_id="19:target@thread.v2", message="🤖 Already prefixed")
    assert repo.captured_message == "🤖 Already prefixed"


def test_resolve_chat_name_returns_name() -> None:
    use_case = ResolveChatNameUseCase(repo=FakeChatRepo())  # type: ignore[arg-type]
    result = use_case.execute(chat_id="19:abc@thread.v2")
    assert result == "Architecture"


def test_resolve_chat_name_passes_chat_id() -> None:
    class CapturingRepo:
        captured_id: str = ""

        def resolve_chat_name(self, chat_id: str) -> str:
            self.captured_id = chat_id
            return "resolved"

    repo = CapturingRepo()
    use_case = ResolveChatNameUseCase(repo=repo)  # type: ignore[arg-type]
    use_case.execute(chat_id="19:xyz@thread.v2")
    assert repo.captured_id == "19:xyz@thread.v2"
