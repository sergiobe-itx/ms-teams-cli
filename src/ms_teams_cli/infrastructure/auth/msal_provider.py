"""MSAL device-code token provider for ms-teams-cli."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import msal  # type: ignore[import-untyped]

from ms_teams_cli.domain.exceptions import AuthenticationError
from ms_teams_cli.infrastructure.auth.token_cache import (
    _CACHE_DIR,  # noqa: SLF001 # type: ignore[private-import]
)

_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph CLI (pre-authorized)
_AUTHORITY = "https://login.microsoftonline.com/organizations"
_SCOPES = ["https://graph.microsoft.com/.default"]


def _msal_cache_path() -> Path:
    return Path(os.environ.get("TEAMS_MSAL_CACHE", str(_CACHE_DIR / "msal_cache.json")))  # type: ignore[arg-type]


def _load_msal_cache(path: Path) -> Any:  # noqa: ANN401
    cache = msal.SerializableTokenCache()
    if path.exists():
        cache.deserialize(path.read_text(encoding="utf-8"))  # type: ignore[no-untyped-call]
    return cache


def _save_msal_cache(cache: Any, path: Path) -> None:  # noqa: ANN401
    if cache.has_state_changed:  # type: ignore[no-untyped-call]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(cache.serialize(), encoding="utf-8")  # type: ignore[no-untyped-call]
        tmp.chmod(0o600)
        tmp.replace(path)


class MsalGraphTokenProvider:
    """Acquire Microsoft Graph tokens via MSAL device-code flow."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self._cache_path = cache_path or _msal_cache_path()
        self._token_cache = _load_msal_cache(self._cache_path)
        self._app = msal.PublicClientApplication(  # type: ignore[no-untyped-call]
            client_id=_CLIENT_ID,
            authority=_AUTHORITY,
            token_cache=self._token_cache,
        )

    def get_token(self) -> str:
        """Return a valid access token via silent acquisition, or raise AuthenticationError."""
        accounts = self._app.get_accounts()  # type: ignore[no-untyped-call]
        if accounts:
            result = self._app.acquire_token_silent(  # type: ignore[no-untyped-call]
                scopes=_SCOPES, account=accounts[0]
            )
            if result and "access_token" in result:
                _save_msal_cache(self._token_cache, self._cache_path)
                return str(result["access_token"])  # type: ignore[arg-type]
        raise AuthenticationError(
            "Not logged in via MSAL. Run: ms-teams login"
        )

    def renew(self) -> str:
        """Force token renewal using the MSAL refresh token."""
        accounts = self._app.get_accounts()  # type: ignore[no-untyped-call]
        if accounts:
            result = self._app.acquire_token_silent(  # type: ignore[no-untyped-call]
                scopes=_SCOPES, account=accounts[0], force_refresh=True
            )
            if result and "access_token" in result:
                _save_msal_cache(self._token_cache, self._cache_path)
                return str(result["access_token"])  # type: ignore[arg-type]
        raise AuthenticationError(
            "Token renewal failed. Not logged in via MSAL. Run: ms-teams login"
        )

    def login(self) -> str:
        """Run device-code flow, cache the token, and return the access token."""
        flow = self._app.initiate_device_flow(scopes=_SCOPES)  # type: ignore[no-untyped-call]
        if "user_code" not in flow:
            error_desc: str = flow.get("error_description", "unknown error")  # type: ignore[no-untyped-call]
            raise AuthenticationError(f"Device flow initiation failed: {error_desc}")
        print(f"To sign in, visit:  {flow['verification_uri']}", file=sys.stderr)
        print(f"Enter code:         {flow['user_code']}", file=sys.stderr)
        print("Waiting for authentication...", file=sys.stderr)
        result = self._app.acquire_token_by_device_flow(flow)  # type: ignore[no-untyped-call]
        if "access_token" not in result:
            error_desc = str(result.get("error_description", result.get("error", "unknown")))  # type: ignore[no-untyped-call]
            raise AuthenticationError(f"Login failed: {error_desc}")  # type: ignore[arg-type]
        _save_msal_cache(self._token_cache, self._cache_path)
        return str(result["access_token"])  # type: ignore[arg-type]

    def logout(self) -> None:
        """Remove the MSAL token cache."""
        if self._cache_path.exists():
            self._cache_path.unlink()


