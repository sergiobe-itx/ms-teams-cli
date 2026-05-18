"""Microsoft Graph API HTTP client."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

import httpx

from ms_teams_cli.domain.exceptions import GraphAPIError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ms_teams_cli.domain.ports import GraphTokenProvider


GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"


def _extract_error_message(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    payload_dict = cast("dict[str, object]", payload)
    error_payload = payload_dict.get("error")
    if not isinstance(error_payload, dict):
        return ""
    error_dict = cast("dict[str, object]", error_payload)
    message = error_dict.get("message")
    if not isinstance(message, str):
        return ""
    return message[:120]


def _as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    values = cast("list[object]", value)
    items: list[dict[str, object]] = []
    for item in values:
        if isinstance(item, dict):
            items.append(cast("dict[str, object]", item))
    return items


class GraphClient:
    """HTTP client for Microsoft Graph API with automatic token renewal."""

    def __init__(self, token_provider: GraphTokenProvider) -> None:
        self._provider: GraphTokenProvider = token_provider

    def get(self, url: str) -> dict[str, object]:
        """GET url with Bearer token, retry once on 401 with renewed token."""
        token = self._provider.get_token()
        with httpx.Client(timeout=20) as client:
            response = client.get(
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            if response.status_code == 401:
                token = self._provider.renew()
                response = client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )

        if not response.is_success:
            body = ""
            try:
                body = _extract_error_message(cast("object", response.json()))
            except Exception:
                body = ""
            raise GraphAPIError(
                f"Graph API HTTP {response.status_code} — {body}",
                status_code=response.status_code,
                url=url,
            )

        data = cast("object", response.json())
        if isinstance(data, dict):
            return cast("dict[str, object]", data)
        return {"value": data}

    def paginate(
        self,
        url: str,
        max_pages: int = 1,
        stop_before: str | None = None,
    ) -> Iterator[dict[str, object]]:
        """Yield paginated Graph items lazily up to max_pages."""
        page = 0
        next_url: str | None = url
        while next_url and page < max_pages:
            data = self.get(next_url)
            items = _as_dict_list(data.get("value", []))
            yield from items
            page += 1
            next_url_value = data.get("@odata.nextLink")
            next_url = next_url_value if isinstance(next_url_value, str) else None
            if stop_before and items:
                dates = [
                    created
                    for item in items
                    if isinstance(created := item.get("createdDateTime"), str) and created
                ]
                if dates and min(dates)[:10] < stop_before:
                    break
