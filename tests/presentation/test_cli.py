"""CLI presentation tests — commands, error handling, and smoke tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Final, cast, override

import pytest
import typer
from loguru import logger
from typer.core import TyperGroup
from typer.testing import CliRunner

import ms_teams_cli.infrastructure.auth as auth_module
import ms_teams_cli.infrastructure.auth.az_provider as az_provider_module
import ms_teams_cli.infrastructure.auth.token_cache as token_cache_module
import ms_teams_cli.infrastructure.chat as chat_module
import ms_teams_cli.infrastructure.chat.client as chat_client_module
import ms_teams_cli.presentation.cli as cli_module
import ms_teams_cli.presentation.dependencies as deps_module
import ms_teams_cli.presentation.formatters as formatters_module
from ms_teams_cli import (
    APIError,
    AuthenticationError,
    Channel,
    ChannelMessage,
    ChannelService,
    Chat,
    ChatMessage,
    ChatService,
    ScanResult,
    Team,
    TeamsError,
    __all__,
    __version__,
)
from ms_teams_cli.domain.entities import ChatType, MessageAuthor, MessageBody

runner = CliRunner()
app = cli_module.app


def _record_disable(calls: list[str], name: str) -> None:
    calls.append(f"disable:{name}")


def _record_enable(calls: list[str], name: str) -> None:
    calls.append(f"enable:{name}")


def _record_echo(captured: list[tuple[str, bool]], message: object, err: bool = False) -> None:
    captured.append((str(message), err))


def _prompt_url(_text: str) -> str:
    return "https://teams.microsoft.com/l/team/abc123"


def _decline_prompt(_text: str, default: str = "N") -> str:
    del default
    return "n"


ARCHITECTURE_NAME: Final = "Architecture"


class _FakeUseCase:
    def __init__(self, return_value: object = None, side_effect: Exception | None = None) -> None:
        self._return_value = return_value
        self._side_effect = side_effect
        self.calls: list[dict[str, object]] = []

    def execute(self, *args: object, **kwargs: object) -> object:
        self.calls.append({"args": args, "kwargs": kwargs})
        if self._side_effect is not None:
            raise self._side_effect
        return self._return_value


class FakeTokenCache:
    path: Path

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("/tmp/graph-token.json")

    def load(self) -> str | None:
        return "token"


class FakeChatTokenCache:
    path: Path

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("/tmp/chat-token.json")

    def load(self) -> tuple[str, str] | None:
        return ("token", "https://chat.example.test")


class FakeGraphTokenProvider:
    should_raise: Exception | None = None
    cache: FakeTokenCache | None

    def __init__(self, cache: FakeTokenCache | None = None) -> None:
        self.cache = cache

    def renew(self) -> str:
        if self.should_raise is not None:
            raise self.should_raise
        return "token"


class FakeChatTokenProvider:
    cache: FakeChatTokenCache | None

    def __init__(self, cache: FakeChatTokenCache | None = None) -> None:
        self.cache = cache


class FakeGraphClientFactory:
    token_provider: FakeGraphTokenProvider

    def __init__(self, token_provider: FakeGraphTokenProvider) -> None:
        self.token_provider = token_provider


class FakeChatClientFactory:
    token_provider: FakeChatTokenProvider

    def __init__(self, token_provider: FakeChatTokenProvider) -> None:
        self.token_provider = token_provider


def _sample_channel_message(message_id: str = "m1") -> ChannelMessage:
    return ChannelMessage(
        id=message_id,
        createdDateTime="2024-01-15T14:30:00Z",
        author=MessageAuthor(displayName="Alice"),
        body=MessageBody(content="<p>Hello</p>", contentType="html"),
        replyCount=0,
        messageType="message",
        replyToId=None,
    )


# === Smoke / version tests ===


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in [
        "version",
        "teams",
        "channels",
        "messages",
        "replies",
        "unanswered",
        "scan",
        "parse-url",
        "token",
        "chats",
        "unread",
        "chat-messages",
        "send-message",
    ]:
        assert command in result.output


def test_each_command_help_exits_zero() -> None:
    for command in [
        "version",
        "teams",
        "channels",
        "messages",
        "replies",
        "unanswered",
        "scan",
        "parse-url",
        "token",
        "chats",
        "unread",
        "chat-messages",
        "send-message",
    ]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "ms-teams-cli 0.1.0" in result.output


def test_verbose_flag_is_accepted() -> None:
    result = runner.invoke(app, ["-v", "version"])

    assert result.exit_code == 0
    assert "ms-teams-cli 0.1.0" in result.output


# === Callback / error handler tests ===


def test_main_callback_disables_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_disable(name: str) -> None:
        _record_disable(calls, name)

    monkeypatch.setattr(logger, "disable", fake_disable)

    cli_module.main(verbose=0)

    assert calls == ["disable:ms_teams_cli"]


def test_main_callback_enables_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_enable(name: str) -> None:
        _record_enable(calls, name)

    monkeypatch.setattr(logger, "enable", fake_enable)

    cli_module.main(verbose=2)

    assert calls == ["enable:ms_teams_cli"]


def test_global_error_handler_for_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, bool]] = []

    def fake_super_main(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise SystemExit(130)

    monkeypatch.setattr(TyperGroup, "main", fake_super_main)
    def fake_echo(message: object, err: bool = False) -> None:
        _record_echo(captured, message, err)

    monkeypatch.setattr(typer, "echo", fake_echo)

    group = cli_module.TeamsTyperGroup(name="ms-teams")

    try:
        _ = group.main([])
    except SystemExit as exc:
        assert exc.code == 130
    else:
        raise AssertionError("Expected SystemExit")

    assert captured == [("Cancelled.", True)]


def test_global_error_handler_for_uncaught_teams_error(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, bool]] = []

    def fake_super_main(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise TeamsError("boom")

    monkeypatch.setattr(TyperGroup, "main", fake_super_main)
    def fake_echo(message: object, err: bool = False) -> None:
        _record_echo(captured, message, err)

    monkeypatch.setattr(typer, "echo", fake_echo)

    group = cli_module.TeamsTyperGroup(name="ms-teams")

    try:
        _ = group.main([])
    except typer.Exit as exc:
        assert exc.exit_code == 1
    else:
        raise AssertionError("Expected typer.Exit")

    assert captured == [("boom", True)]


def test_global_error_handler_reraises_non_interrupt_system_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_super_main(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise SystemExit(2)

    monkeypatch.setattr(TyperGroup, "main", fake_super_main)

    group = cli_module.TeamsTyperGroup(name="ms-teams")

    with pytest.raises(SystemExit, match="2"):
        _ = group.main([])


# === Package public API ===


def test_package_public_api_exports() -> None:
    expected = {
        "__version__",
        "ChannelService",
        "ChatService",
        "TeamsError",
        "AuthenticationError",
        "APIError",
        "Team",
        "Channel",
        "ChannelMessage",
        "Chat",
        "ChatMessage",
        "ScanResult",
    }

    assert set(__all__) == expected
    assert ChannelService is not None
    assert ChatService is not None
    assert TeamsError is not None
    assert AuthenticationError is not None
    assert APIError is not None
    assert Team is not None
    assert Channel is not None
    assert ChannelMessage is not None
    assert Chat is not None
    assert ChatMessage is not None
    assert ScanResult is not None


def test_cli_main_guard_is_last_line() -> None:
    content = Path(cli_module.__file__).read_text(encoding="utf-8").strip().splitlines()

    assert content[-2] == 'if __name__ == "__main__":'
    assert content[-1] == "    app()"


# === Channel CLI commands ===


def test_teams_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    teams = [
        Team(id="t1", displayName="Team A", description="desc"),
        Team(id="t2", displayName="Team B", description=None),
    ]

    monkeypatch.setattr(deps_module, "get_list_teams", lambda: _FakeUseCase(teams))

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

    monkeypatch.setattr(deps_module, "get_list_teams", lambda: _FakeUseCase(teams))

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

    monkeypatch.setattr(deps_module, "get_list_channels", lambda: _FakeUseCase(channels))

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

    monkeypatch.setattr(deps_module, "get_list_channels", lambda: _FakeUseCase(channels))

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


def test_messages_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = [
        ChannelMessage(
            id="m1",
            createdDateTime="2024-01-15T14:30:00Z",
            author=MessageAuthor(displayName="Alice Johnson"),
            body=MessageBody(content="<p>Hello</p>", contentType="html"),
            replyCount=3,
            messageType="message",
            replyToId=None,
        ),
        ChannelMessage(
            id="m2",
            createdDateTime="2024-01-15T14:31:00Z",
            author=MessageAuthor(displayName="Bob Smith"),
            body=MessageBody(content="<p>Hi</p>", contentType="html"),
            replyCount=0,
            messageType="message",
            replyToId=None,
        ),
    ]

    monkeypatch.setattr(deps_module, "get_get_messages", lambda: _FakeUseCase(messages))

    captured: list[list[ChannelMessage]] = []

    def fake_formatter(items: list[ChannelMessage]) -> None:
        captured.append(items)
        for item in items:
            print(item.author.display_name)
        print(f"{len(items)} messages.")

    monkeypatch.setattr(formatters_module, "format_messages_table", fake_formatter)

    result = runner.invoke(app, ["messages", "--team", "t1", "--channel", "c1"])

    assert result.exit_code == 0
    assert captured == [messages]
    assert "Alice Johnson" in result.stdout
    assert "Bob Smith" in result.stdout
    assert "2 messages." in result.stdout


def test_replies_cli_command_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    parent = ChannelMessage(
        id="m1",
        createdDateTime="2024-01-15T14:30:00Z",
        author=MessageAuthor(displayName="Alice Johnson"),
        body=MessageBody(content="<p>Original post</p>", contentType="html"),
        replyCount=1,
        messageType="message",
        replyToId=None,
    )
    reply = ChannelMessage(
        id="r1",
        createdDateTime="2024-01-15T14:31:00Z",
        author=MessageAuthor(displayName="Bob Smith"),
        body=MessageBody(content="<p>Reply</p>", contentType="html"),
        replyCount=0,
        messageType="message",
        replyToId="m1",
    )

    monkeypatch.setattr(deps_module, "get_get_thread", lambda: _FakeUseCase((parent, [reply])))

    captured_parent: list[ChannelMessage] = []
    captured_replies: list[list[ChannelMessage]] = []

    def fake_formatter(p: ChannelMessage, r: list[ChannelMessage]) -> None:
        captured_parent.append(p)
        captured_replies.append(r)
        print(f"From : {p.author.display_name}")
        print(f"Replies ({len(r)} total)")
        for reply_msg in r:
            print(f"  {reply_msg.author.display_name}")

    monkeypatch.setattr(formatters_module, "format_thread", fake_formatter)

    result = runner.invoke(app, ["replies", "--team", "t1", "--channel", "c1", "--thread", "m1"])

    assert result.exit_code == 0
    assert captured_parent == [parent]
    assert captured_replies == [[reply]]
    assert "Alice Johnson" in result.stdout
    assert "Bob Smith" in result.stdout


def test_scan_unanswered_cli_help() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["unanswered", "--help"])
    assert result.exit_code == 0


# === Chat CLI commands ===


def test_chats_cli_help() -> None:
    result = runner.invoke(app, ["chats", "--help"])
    assert result.exit_code == 0


def test_chats_cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    chats = [
        Chat(
            id="19:g1@thread.v2",
            chat_type=ChatType.GROUP,
            display_name="Architecture",
            last_message_preview="Hello",
            last_message_time="2026-03-28T10:30:00.000Z",
        )
    ]

    class _FakeListChats:
        def execute(self, *args: object, **kwargs: object) -> list[Chat]:
            return chats

    monkeypatch.setattr(deps_module, "get_list_chats", lambda: _FakeListChats())

    captured: list[object] = []

    def fake_json_formatter(data: object) -> None:
        captured.append(data)
        print(json.dumps([item.model_dump(by_alias=False) for item in cast("list[Chat]", data)]))

    monkeypatch.setattr(formatters_module, "format_json", fake_json_formatter)

    result = runner.invoke(app, ["chats", "--type", "group", "--top", "10", "--json"])

    assert result.exit_code == 0
    assert captured == [chats]


def test_chats_cli_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(app, ["chats", "--type", "bogus"])

    assert result.exit_code == 1
    assert "Invalid chat type: bogus" in result.stderr


def test_chat_messages_cli_help() -> None:
    result = runner.invoke(app, ["chat-messages", "--help"])
    assert result.exit_code == 0


def test_unread_cli_help() -> None:
    result = runner.invoke(app, ["unread", "--help"])
    assert result.exit_code == 0


def test_send_message_cli_help() -> None:
    result = runner.invoke(app, ["send-message", "--help"])
    assert result.exit_code == 0


# === Empty state commands ===


def test_teams_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_list_teams", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["teams"])

    assert result.exit_code == 0
    assert "No teams found." in result.stdout


def test_channels_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_list_channels", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["channels", "--team", "t1"])

    assert result.exit_code == 0
    assert "No channels found." in result.stdout


def test_messages_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_get_messages", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["messages", "--team", "t1", "--channel", "c1"])

    assert result.exit_code == 0
    assert "No messages found." in result.stdout


def test_replies_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps_module, "get_get_thread", lambda: _FakeUseCase((_sample_channel_message(), []))
    )

    result = runner.invoke(app, ["replies", "--team", "t1", "--channel", "c1", "--thread", "m1"])

    assert result.exit_code == 0
    assert "No replies found." in result.stdout


def test_unanswered_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_find_unanswered", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["unanswered", "--team", "t1", "--channel", "c1"])

    assert result.exit_code == 0
    assert "No unanswered posts" in result.stdout


def test_scan_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps_module,
        "get_scan_activity",
        lambda: _FakeUseCase(ScanResult(date="2024-01-15", channels=[])),
    )

    result = runner.invoke(app, ["scan", "--team", "t1", "--date", "2024-01-15"])

    assert result.exit_code == 0
    assert "No activity found on 2024-01-15." in result.stdout


def test_chats_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_list_chats", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["chats"])

    assert result.exit_code == 0
    assert "No chats found." in result.stdout


def test_unread_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_list_unread", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["unread"])

    assert result.exit_code == 0
    assert "No unread chats." in result.stdout


def test_chat_messages_command_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps_module, "get_chat_messages", lambda: _FakeUseCase([]))

    result = runner.invoke(app, ["chat-messages", "--chat", "19:g1@thread.v2"])

    assert result.exit_code == 0
    assert "No messages found." in result.stdout


# === Send message command ===


def test_send_message_command_cancel(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        deps_module, "get_resolve_chat_name", lambda: _FakeUseCase(ARCHITECTURE_NAME)
    )
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(typer, "prompt", _decline_prompt)

    cli_module.send_message_command(chat_id="19:g1@thread.v2", message="hello")

    assert "Cancelled — message NOT sent." in capsys.readouterr().out


def test_send_message_command_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps_module, "get_resolve_chat_name", lambda: _FakeUseCase(ARCHITECTURE_NAME)
    )
    monkeypatch.setattr(deps_module, "get_send_message", lambda: _FakeUseCase("msg-123"))

    result = runner.invoke(
        app,
        ["send-message", "--chat", "19:g1@thread.v2", "--message", "hello", "--yes"],
    )

    assert result.exit_code == 0
    assert "Message sent. (id: msg-123)" in result.stdout


# === Error handling ===


def test_teams_command_error_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps_module,
        "get_list_teams",
        lambda: _FakeUseCase(side_effect=TeamsError("team failure")),
    )

    result = runner.invoke(app, ["teams"])

    assert result.exit_code == 1
    assert "team failure" in result.stderr


def test_parse_url_requires_argument_when_not_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    result = runner.invoke(app, ["parse-url"])

    assert result.exit_code == 1
    assert "URL argument required" in result.stderr


def test_parse_url_reads_from_prompt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(typer, "prompt", _prompt_url)

    cli_module.parse_url_command(None)

    assert "CHANNEL_ID : abc123" in capsys.readouterr().out


# === Token command ===


def test_token_command_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "graph-token.json"
    _ = cache_path.write_text(json.dumps({"expiresOn": "2026-12-31T00:00:00Z"}), encoding="utf-8")

    class LocalTokenCache(FakeTokenCache):
        def __init__(self) -> None:
            super().__init__(cache_path)

    class LocalTokenProvider(FakeGraphTokenProvider):
        should_raise: Exception | None = None

    monkeypatch.setattr(token_cache_module, "TokenCache", LocalTokenCache)
    monkeypatch.setattr(auth_module, "TokenCache", LocalTokenCache)
    monkeypatch.setattr(auth_module, "TokenCache", LocalTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", LocalTokenProvider)
    monkeypatch.setattr(auth_module, "AzGraphTokenProvider", LocalTokenProvider)
    monkeypatch.setattr(auth_module, "AzGraphTokenProvider", LocalTokenProvider)

    result = runner.invoke(app, ["token"])

    assert result.exit_code == 0
    assert "Token OK, expires: 2026-12-31T00:00:00Z" in result.stdout


def test_token_command_empty_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    class EmptyTokenCache(FakeTokenCache):
        @override
        def load(self) -> str | None:
            return None

    monkeypatch.setattr(token_cache_module, "TokenCache", EmptyTokenCache)
    monkeypatch.setattr(auth_module, "TokenCache", EmptyTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeGraphTokenProvider)
    monkeypatch.setattr(auth_module, "AzGraphTokenProvider", FakeGraphTokenProvider)

    result = runner.invoke(app, ["token"])

    assert result.exit_code == 1
    assert "Token cache is empty after renewal" in result.stderr


def test_token_command_teams_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingProvider(FakeGraphTokenProvider):
        should_raise: Exception | None = TeamsError("renew failed")

    monkeypatch.setattr(token_cache_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(auth_module, "TokenCache", FakeTokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FailingProvider)
    monkeypatch.setattr(auth_module, "AzGraphTokenProvider", FailingProvider)

    result = runner.invoke(app, ["token"])

    assert result.exit_code == 1
    assert "renew failed" in result.stderr


def test_token_command_unexpected_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenCache:
        def __init__(self) -> None:
            pass

        def load(self) -> str | None:
            return "token"

        @property
        def path(self) -> Path:
            raise RuntimeError("boom")

    monkeypatch.setattr(token_cache_module, "TokenCache", BrokenCache)
    monkeypatch.setattr(auth_module, "TokenCache", BrokenCache)
    monkeypatch.setattr(az_provider_module, "AzGraphTokenProvider", FakeGraphTokenProvider)
    monkeypatch.setattr(auth_module, "AzGraphTokenProvider", FakeGraphTokenProvider)

    result = runner.invoke(app, ["token"])

    assert result.exit_code == 1
    assert "Error: boom" in result.stderr


def test_scan_command_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps_module,
        "get_scan_activity",
        lambda: _FakeUseCase(side_effect=ValueError("date must be YYYY-MM-DD")),
    )

    result = runner.invoke(app, ["scan", "--team", "t1", "--date", "bad"])

    assert result.exit_code == 1
    assert "date must be YYYY-MM-DD" in result.stderr


def test_chats_command_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_cache_module, "ChatTokenCache", FakeChatTokenCache)
    monkeypatch.setattr(auth_module, "ChatTokenCache", FakeChatTokenCache)
    monkeypatch.setattr(az_provider_module, "AzChatTokenProvider", FakeChatTokenProvider)
    monkeypatch.setattr(auth_module, "AzChatTokenProvider", FakeChatTokenProvider)
    monkeypatch.setattr(chat_client_module, "ChatServiceClient", FakeChatClientFactory)
    monkeypatch.setattr(chat_module, "ChatServiceClient", FakeChatClientFactory)

    result = runner.invoke(app, ["chats", "--type", "bad"])

    assert result.exit_code == 1
    assert "Invalid chat type: bad" in result.stderr


def test_unread_command_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_cache_module, "ChatTokenCache", FakeChatTokenCache)
    monkeypatch.setattr(auth_module, "ChatTokenCache", FakeChatTokenCache)
    monkeypatch.setattr(az_provider_module, "AzChatTokenProvider", FakeChatTokenProvider)
    monkeypatch.setattr(auth_module, "AzChatTokenProvider", FakeChatTokenProvider)
    monkeypatch.setattr(chat_client_module, "ChatServiceClient", FakeChatClientFactory)
    monkeypatch.setattr(chat_module, "ChatServiceClient", FakeChatClientFactory)

    result = runner.invoke(app, ["unread", "--type", "bad"])

    assert result.exit_code == 1
    assert "Invalid chat type: bad" in result.stderr
