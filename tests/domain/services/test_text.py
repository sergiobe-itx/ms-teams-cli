"""Tests for text utility functions."""
from __future__ import annotations

from ms_teams_cli.domain.services import format_datetime, strip_html


def test_strip_html_removes_tags() -> None:
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_decodes_entities() -> None:
    assert strip_html("Tom &amp; Jerry &lt;3&gt;") == "Tom & Jerry <3>"
    assert strip_html("&nbsp;space&nbsp;") == "space"
    assert strip_html("&apos;quote&apos;") == "'quote'"
    assert strip_html("&quot;hi&quot;") == '"hi"'


def test_strip_html_collapses_whitespace() -> None:
    assert strip_html("<p>  hello   world  </p>") == "hello world"


def test_strip_html_empty_string() -> None:
    assert strip_html("") == ""


def test_strip_html_plain_text() -> None:
    assert strip_html("no tags here") == "no tags here"


def test_format_datetime_slices_iso() -> None:
    assert format_datetime("2024-01-15T14:30:00Z") == "2024-01-15 14:30"


def test_format_datetime_custom_length() -> None:
    assert format_datetime("2024-01-15T14:30:00Z", 10) == "2024-01-15"


def test_format_datetime_replaces_t() -> None:
    result = format_datetime("2024-01-15T14:30:00Z")
    assert "T" not in result
