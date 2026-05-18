"""Tests for presentation formatters."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ms_teams_cli.domain.entities import (
    Channel,
    ChannelActivity,
    ChannelMessage,
    Chat,
    ChatMessage,
    ChatType,
    MessageAuthor,
    MessageBody,
    ScanResult,
    Team,
    ThreadActivity,
)
from ms_teams_cli.presentation import formatters

if TYPE_CHECKING:
    import pytest


def _channel_message(
    *,
    message_id: str,
    author: str = "Alice",
    content: str = "<p>Hello</p>",
    created: str = "2024-01-15T14:30:00Z",
    reply_count: int | None = 0,
    message_type: str = "message",
    reply_to_id: str | None = None,
) -> ChannelMessage:
    return ChannelMessage(
        id=message_id,
        createdDateTime=created,
        author=MessageAuthor(displayName=author),
        body=MessageBody(content=content, contentType="html"),
        replyCount=reply_count,
        messageType=message_type,
        replyToId=reply_to_id,
    )


def _chat(
    *,
    chat_id: str = "19:g1@thread.v2",
    chat_type: ChatType = ChatType.GROUP,
    display_name: str = "Architecture",
    preview: str | None = "Latest update",
    when: str | None = "2024-01-15T14:30:00Z",
) -> Chat:
    return Chat(
        id=chat_id,
        chat_type=chat_type,
        display_name=display_name,
        last_message_preview=preview,
        last_message_time=when,
    )


def test_format_teams_table_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_teams_table([])

    assert "No teams found." in capsys.readouterr().out


def test_format_teams_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_teams_table([Team(id="t1", displayName="Team A")])

    out = capsys.readouterr().out
    assert "TEAM" in out
    assert "Team A" in out
    assert "1 teams." in out


def test_format_channels_table_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_channels_table([])

    assert "No channels found." in capsys.readouterr().out


def test_format_channels_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_channels_table([Channel(id="c1", displayName="General")])

    out = capsys.readouterr().out
    assert "CHANNEL" in out
    assert "General" in out
    assert "1 channels." in out


def test_format_json_with_models(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_json([Team(id="t1", displayName="Team A")])

    out = capsys.readouterr().out
    assert '"display_name": "Team A"' in out


def test_format_json_plain_data(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_json({"ok": True})

    assert '"ok": true' in capsys.readouterr().out


def test_format_messages_table_empty_when_non_message_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_messages_table([
        _channel_message(message_id="m1", message_type="systemEventMessage")
    ])

    assert "No messages found." in capsys.readouterr().out


def test_format_messages_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_messages_table([
        _channel_message(message_id="m1", author="Alice", content="<p>Hello <b>world</b></p>"),
        _channel_message(message_id="m2", author="Bob", reply_to_id="m1"),
    ])

    out = capsys.readouterr().out
    assert "AUTHOR" in out
    assert "Alice" in out
    assert "Bob" in out
    assert "Hello world" in out
    assert "2 messages." in out


def test_format_thread_with_replies(capsys: pytest.CaptureFixture[str]) -> None:
    parent = _channel_message(message_id="m1", author="Alice", content="<p>Parent</p>")
    reply = _channel_message(
        message_id="r1",
        author="Bob",
        content="<p>Reply</p>",
        reply_to_id="m1",
    )

    formatters.format_thread(parent, [reply])

    out = capsys.readouterr().out
    assert "ORIGINAL POST" in out
    assert "Alice" in out
    assert "Bob" in out
    assert "1 replies." in out


def test_format_thread_without_replies(capsys: pytest.CaptureFixture[str]) -> None:
    parent = _channel_message(message_id="m1")

    formatters.format_thread(parent, [])

    out = capsys.readouterr().out
    assert "No replies found." in out
    assert "0 replies." in out


def test_format_unanswered_table_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_unanswered_table([], 30)

    assert "No unanswered posts in last 30 min." in capsys.readouterr().out


def test_format_unanswered_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_unanswered_table([_channel_message(message_id="m1", author="Alice")], 60)

    out = capsys.readouterr().out
    assert "Posts without replies in last 60 min:" in out
    assert "Alice" in out
    assert "1 unanswered posts" in out


def test_format_scan_result_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_scan_result(ScanResult(date="2024-01-15", channels=[]))

    assert "No activity found on 2024-01-15." in capsys.readouterr().out


def test_format_scan_result_with_activity(capsys: pytest.CaptureFixture[str]) -> None:
    root = _channel_message(message_id="m1", author="Alice", content="<p>Root</p>")
    reply = _channel_message(message_id="r1", author="Bob", content="<p>Reply</p>")
    result = ScanResult(
        date="2024-01-15",
        channels=[
            ChannelActivity(
                channel_name="General",
                channel_id="c1",
                threads=[
                    ThreadActivity(
                        root_message=root,
                        replies_on_date=[reply],
                        root_created_on_date=True,
                    )
                ],
            )
        ],
    )

    formatters.format_scan_result(result)

    out = capsys.readouterr().out
    assert "General" in out
    assert "Alice: Root" in out
    assert "Bob" in out
    assert "TOTAL 2024-01-15: 1 new posts | 1 replies" in out


def test_format_chats_table_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_chats_table([])

    assert "No chats found." in capsys.readouterr().out


def test_format_chats_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_chats_table([_chat()])

    out = capsys.readouterr().out
    assert "TYPE" in out
    assert "Architecture" in out
    assert "1 conversations." in out


def test_format_unread_table_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_unread_table([])

    assert "No unread chats." in capsys.readouterr().out


def test_format_unread_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_unread_table(
        [_chat(chat_type=ChatType.ONE_TO_ONE, display_name="Chat with Alice")]
    )

    out = capsys.readouterr().out
    assert "Chat with Alice" in out
    assert "1 unread conversations." in out


def test_format_chat_messages_table_empty(capsys: pytest.CaptureFixture[str]) -> None:
    formatters.format_chat_messages_table([])

    assert "No messages found." in capsys.readouterr().out


def test_format_chat_messages_table_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(formatters, "_is_tty", lambda: False)

    formatters.format_chat_messages_table(
        [
            ChatMessage(
                id="1",
                composetime="2024-01-15T14:30:00Z",
                imdisplayname="Alice",
                content="<p>Hello</p>",
            )
        ]
    )

    out = capsys.readouterr().out
    assert "WHEN" in out
    assert "Alice" in out
    assert "Hello" in out
    assert "1 messages." in out
