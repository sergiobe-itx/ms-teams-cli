"""Composition root — wires the complete object graph."""

from __future__ import annotations

from ms_teams_cli.application.use_cases import (
    FindUnansweredUseCase,
    GetChatMessagesUseCase,
    GetMessagesUseCase,
    GetThreadUseCase,
    ListCalendarEventsUseCase,
    ListChannelsUseCase,
    ListChatsUseCase,
    ListTeamsUseCase,
    ListUnreadUseCase,
    ResolveChatNameUseCase,
    ScanActivityUseCase,
    SendMessageUseCase,
)
from ms_teams_cli.infrastructure.auth import (
    AzChatTokenProvider,
    AzGraphTokenProvider,
    ChatTokenCache,
    TokenCache,
)
from ms_teams_cli.infrastructure.chat import ChatServiceClient, ChatServiceRepository
from ms_teams_cli.infrastructure.graph import (
    GraphCalendarRepository,
    GraphChannelRepository,
    GraphClient,
)


def _build_channel_repo() -> GraphChannelRepository:
    provider = AzGraphTokenProvider(cache=TokenCache())
    client = GraphClient(token_provider=provider)
    return GraphChannelRepository(graph_client=client)


def _build_chat_repo() -> ChatServiceRepository:
    provider = AzChatTokenProvider(cache=ChatTokenCache())
    client = ChatServiceClient(token_provider=provider)
    return ChatServiceRepository(chat_client=client)


def get_list_teams() -> ListTeamsUseCase:
    return ListTeamsUseCase(repo=_build_channel_repo())


def get_list_channels() -> ListChannelsUseCase:
    return ListChannelsUseCase(repo=_build_channel_repo())


def get_get_messages() -> GetMessagesUseCase:
    return GetMessagesUseCase(repo=_build_channel_repo())


def get_get_thread() -> GetThreadUseCase:
    return GetThreadUseCase(repo=_build_channel_repo())


def get_find_unanswered() -> FindUnansweredUseCase:
    return FindUnansweredUseCase(repo=_build_channel_repo())


def get_scan_activity() -> ScanActivityUseCase:
    return ScanActivityUseCase(repo=_build_channel_repo())


def get_list_chats() -> ListChatsUseCase:
    return ListChatsUseCase(repo=_build_chat_repo())


def get_list_unread() -> ListUnreadUseCase:
    return ListUnreadUseCase(repo=_build_chat_repo())


def get_chat_messages() -> GetChatMessagesUseCase:
    return GetChatMessagesUseCase(repo=_build_chat_repo())


def get_send_message() -> SendMessageUseCase:
    return SendMessageUseCase(repo=_build_chat_repo())


def get_resolve_chat_name() -> ResolveChatNameUseCase:
    return ResolveChatNameUseCase(repo=_build_chat_repo())


def _build_calendar_repo() -> GraphCalendarRepository:
    provider = AzGraphTokenProvider(cache=TokenCache())
    client = GraphClient(token_provider=provider)
    return GraphCalendarRepository(graph_client=client)


def get_list_calendar_events() -> ListCalendarEventsUseCase:
    return ListCalendarEventsUseCase(repo=_build_calendar_repo())
