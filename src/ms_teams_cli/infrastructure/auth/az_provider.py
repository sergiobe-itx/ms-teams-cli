"""Azure CLI token providers for ms-teams-cli."""
from __future__ import annotations

import json
import re
import subprocess
from typing import cast

from ms_teams_cli.domain.exceptions import AuthenticationError
from ms_teams_cli.infrastructure.auth.token_cache import TokenCache

_GRAPH_RESOURCE = "https://graph.microsoft.com"


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
