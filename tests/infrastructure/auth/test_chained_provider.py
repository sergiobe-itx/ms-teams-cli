"""Tests for ChainedTokenProvider."""
from __future__ import annotations

import pytest

from ms_teams_cli.domain.exceptions import AuthenticationError
from ms_teams_cli.infrastructure.auth.chained_provider import ChainedTokenProvider


class _OKProvider:
    def __init__(self, token: str = "good") -> None:
        self._token = token
        self.called = False

    def get_token(self) -> str:
        self.called = True
        return self._token


class _FailProvider:
    def __init__(self, msg: str = "fail") -> None:
        self._msg = msg
        self.called = False

    def get_token(self) -> str:
        self.called = True
        raise AuthenticationError(self._msg)


class _ErrorProvider:
    def get_token(self) -> str:
        raise ValueError("unexpected")


def test_first_provider_succeeds_immediately() -> None:
    provider1 = _OKProvider("token-from-1")
    provider2 = _OKProvider("token-from-2")
    chain = ChainedTokenProvider([provider1, provider2])  # type: ignore[list-item]

    result = chain.get_token()

    assert result == "token-from-1"
    assert provider1.called
    assert not provider2.called


def test_falls_back_to_second_provider_on_auth_error() -> None:
    provider1 = _FailProvider("first failed")
    provider2 = _OKProvider("token-from-2")
    chain = ChainedTokenProvider([provider1, provider2])  # type: ignore[list-item]

    result = chain.get_token()

    assert result == "token-from-2"
    assert provider1.called
    assert provider2.called


def test_raises_when_all_fail() -> None:
    provider1 = _FailProvider("first failed")
    provider2 = _FailProvider("second failed")
    chain = ChainedTokenProvider([provider1, provider2])  # type: ignore[list-item]

    with pytest.raises(AuthenticationError, match="ms-teams login"):
        chain.get_token()


def test_non_auth_error_propagates() -> None:
    provider1 = _ErrorProvider()
    provider2 = _OKProvider("should-not-reach")
    chain = ChainedTokenProvider([provider1, provider2])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="unexpected"):
        chain.get_token()
