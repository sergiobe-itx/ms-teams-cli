"""Text utilities for ms-teams-cli."""
from __future__ import annotations

import re


def strip_html(html: str) -> str:
    """Strip HTML tags and decode common entities."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    for entity, char in [
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&apos;", "'"),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ]:
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def format_datetime(iso: str, length: int = 16) -> str:
    """Format an ISO datetime string by slicing to length and replacing T with space."""
    return iso[:length].replace("T", " ")
