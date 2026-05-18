"""Token cache for ms-teams-cli."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

TOKEN_MARGIN: int = 300
_CACHE_DIR = Path.home() / ".cache" / "ms-teams-cli"


def _graph_cache_path() -> Path:
    return Path(os.environ.get("TEAMS_TOKEN_CACHE", _CACHE_DIR / "graph-token.json"))


def _chat_cache_path() -> Path:
    return Path(os.environ.get("TEAMS_SKYPE_TOKEN_CACHE", _CACHE_DIR / "chat-token.json"))


def _atomic_write(path: Path, payload: dict[str, str | int]) -> None:
    _ = path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    _ = temp_path.write_text(json.dumps(payload), encoding="utf-8")
    _ = temp_path.replace(path)


class TokenCache:
    """Cache for Microsoft Graph API access tokens."""

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path or _graph_cache_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> str | None:
        """Return cached token if it remains valid beyond the renewal margin."""
        try:
            data = cast(
                "dict[str, object]", json.loads(self._path.read_text(encoding="utf-8"))
            )
            token = data.get("token")
            expires_on = data.get("expiresOn")
            if not isinstance(token, str) or not isinstance(expires_on, str):
                return None
            exp_ts = int(
                datetime.fromisoformat(expires_on.replace("Z", "+00:00")).timestamp()
            )
        except Exception:
            return None
        now = int(datetime.now(UTC).timestamp())
        return token if exp_ts > now + TOKEN_MARGIN else None

    def save(self, token: str, expires_on: str) -> None:
        """Persist token and expiry to cache file."""
        _atomic_write(self._path, {"token": token, "expiresOn": expires_on})


class ChatTokenCache:
    """Cache for Teams Chat Service tokens."""

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path or _chat_cache_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> tuple[str, str] | None:
        """Return cached chat token and service URL if still valid."""
        try:
            data = cast(
                "dict[str, object]", json.loads(self._path.read_text(encoding="utf-8"))
            )
            skype_token = data.get("skypeToken")
            chat_service = data.get("chatService")
            expires_at = data.get("expiresAt")
            if not isinstance(skype_token, str) or not isinstance(chat_service, str):
                return None
            if not isinstance(expires_at, int):
                return None
        except Exception:
            return None
        now = int(datetime.now(UTC).timestamp())
        return (skype_token, chat_service) if expires_at > now + TOKEN_MARGIN else None

    def save(self, skype_token: str, chat_service: str, expires_at: int) -> None:
        """Persist chat token metadata to cache file."""
        _atomic_write(
            self._path,
            {
                "skypeToken": skype_token,
                "chatService": chat_service,
                "expiresAt": expires_at,
            },
        )
