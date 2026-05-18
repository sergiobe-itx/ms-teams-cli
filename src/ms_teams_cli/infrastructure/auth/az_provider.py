"""Azure CLI token providers for ms-teams-cli."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from typing import cast

import httpx

from ms_teams_cli.domain.exceptions import AuthenticationError
from ms_teams_cli.infrastructure.auth.token_cache import ChatTokenCache, TokenCache

_GRAPH_RESOURCE = "https://graph.microsoft.com"
_SKYPE_RESOURCE = "https://api.spaces.skype.com"
_AUTHZ_URL = "https://authsvc.teams.microsoft.com/v1.0/authz"
_DEFAULT_CHAT_SERVICE = "https://emea.ng.msg.teams.microsoft.com"


def _run_az_get_token(resource: str) -> dict[str, str]:
    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource, "-o", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        details = f"\n{stderr}" if stderr else ""
        raise AuthenticationError(f"az login required. Run: az login{details}")
    data = cast("dict[str, object]", json.loads(result.stdout))
    access_token = data.get("accessToken")
    expires_on = data.get("expiresOn")
    if not isinstance(access_token, str) or not isinstance(expires_on, str):
        raise AuthenticationError("Incomplete az token response.")
    return {"accessToken": access_token, "expiresOn": expires_on}


def _normalize_az_date(raw: str) -> str:
    return re.sub(r"\.\d+$", "", raw.replace(" ", "T")) + "Z"


class AzGraphTokenProvider:
    """Acquire Graph API tokens via Azure CLI."""

    def __init__(self, cache: TokenCache | None = None) -> None:
        self._cache: TokenCache = cache or TokenCache()

    def get_token(self) -> str:
        cached = self._cache.load()
        if cached is not None:
            return cached
        return self.renew()

    def renew(self) -> str:
        data = _run_az_get_token(_GRAPH_RESOURCE)
        token = data["accessToken"]
        expires_on = _normalize_az_date(data["expiresOn"])
        self._cache.save(token, expires_on)
        return token


class AzChatTokenProvider:
    """Acquire Teams Chat Service tokens via Azure CLI and exchange."""

    def __init__(self, cache: ChatTokenCache | None = None) -> None:
        self._cache: ChatTokenCache = cache or ChatTokenCache()

    def get_token(self) -> tuple[str, str]:
        cached = self._cache.load()
        if cached is not None:
            return cached
        return self.renew()

    def renew(self) -> tuple[str, str]:
        aad_data = _run_az_get_token(_SKYPE_RESOURCE)
        aad_token = aad_data["accessToken"]
        try:
            response = httpx.post(
                _AUTHZ_URL,
                json={"resourceUrl": _SKYPE_RESOURCE},
                headers={
                    "Authorization": f"Bearer {aad_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=20,
            )
            _ = response.raise_for_status()
            authz = cast("dict[str, object]", response.json())
        except Exception as exc:
            raise AuthenticationError(f"Skype token exchange failed: {exc}") from exc
        tokens_obj = authz.get("tokens")
        region_gtms_obj = authz.get("regionGtms")
        if not isinstance(tokens_obj, dict):
            raise AuthenticationError("Skype token exchange returned no token payload.")
        tokens = cast("dict[str, object]", tokens_obj)
        skype_token = tokens.get("skypeToken")
        expires_in = tokens.get("expiresIn", 3600)
        chat_service = _DEFAULT_CHAT_SERVICE
        if isinstance(region_gtms_obj, dict):
            region_gtms = cast("dict[str, object]", region_gtms_obj)
            chat_service = region_gtms.get("chatService", _DEFAULT_CHAT_SERVICE)
        if not isinstance(skype_token, str) or not isinstance(expires_in, int):
            raise AuthenticationError("Skype token exchange returned incomplete token data.")
        if not isinstance(chat_service, str):
            chat_service = _DEFAULT_CHAT_SERVICE
        now = int(datetime.now(UTC).timestamp())
        self._cache.save(skype_token, chat_service, now + expires_in)
        return skype_token, chat_service
