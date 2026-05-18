## [2026-05-18] Task 1: Skeleton

### Setup Completed
- Created src/ms_teams_cli/ package structure with domain/infrastructure/application/presentation layers
- Added pyproject.toml with build-system (hatchling), dependencies, and tool configs
- Configured ruff (E,F,I,N,W,UP,B,C4,SIM,TCH,ANN), pyright (strict), pytest, coverage
- Created tests/ with conftest.py and smoke test

### Key Findings
1. **Build system required**: uv needs `[build-system]` with hatchling to install entry points
2. **Typer CLI needs commands**: Empty Typer app fails with "Could not get a command". Added minimal `version` command
3. **Ruff ANN rules**: ANN101/ANN102 don't exist in current ruff version - added to ignore list
4. **Pyright strict mode**: Works fine on empty modules with `reportMissingModuleSource = false`
5. **Module docstrings**: Essential for public API documentation and IDE tooltips

### Project Structure
```
src/ms_teams_cli/
├── __init__.py (version, __all__)
├── py.typed (PEP 561 marker)
├── domain/ (models, exceptions - stubs)
├── infrastructure/ (empty)
├── application/ (empty)
└── presentation/cli.py (Typer app with version command)
```

### Tooling Stack
- Python 3.13 with uv package manager
- Ruff for linting (100 char line length)
- Pyright for type checking (strict mode)
- Pytest for testing
- Typer for CLI framework
- Pydantic, httpx, rich, loguru as core deps

### All Checks Passing
✓ ruff check src/ tests/
✓ pyright src/
✓ pytest tests/ -v (1 passed)
✓ uv run ms-teams --help (exit 0)

## [2026-05-18] Task 2: Auth Kernel
- Kept the auth shared kernel structural: protocol-only domain contracts, cache/provider infra implementations, and no base classes.
- Mirrored _src.py token semantics with proactive renewal margin, XDG-aware cache paths plus env overrides, az date normalization, and Teams authz token exchange payload/headers.
- Tests cover cache validity boundaries, default cache path resolution, Azure CLI failure handling, subprocess bypass on cache hits, and the two-step chat token exchange contract.

## [2026-05-18] Task 3: GraphClient + list-teams
- Added a strict GraphClient with one-shot 401 renewal and a lazy paginate() generator that follows @odata.nextLink and supports stop_before short-circuiting.
- Kept the vertical slice layered: Team Pydantic model -> ChannelService list_teams() -> presentation formatters -> Typer teams command with --json output and TeamsError handling.
- Tests validate Graph HTTP behavior, pagination boundaries, service mapping, and CLI output wiring; current suite passes with 21 tests total.

## [2026-05-18] Task 4: list-channels

### Implementation Pattern
- Followed exact same pattern as Task 3 (list-teams) for consistency
- Added Channel model to domain/models.py with same structure as Team (id, display_name, description)
- Added list_channels(team_id: str) method to ChannelService alongside list_teams()
- Added format_channels_table() to formatters.py with plain text (106-char separator) and Rich table output
- Added channels_command with --team (required) and --json options to cli.py

### Key Decisions
1. **URL construction**: Used f-string in method body rather than module constant to keep URL logic localized
2. **Payload helper**: Created _as_channel_payloads() alongside _as_team_payloads() for type safety
3. **Line length**: Broke long list comprehension into intermediate variable to stay under 100 chars
4. **Tests**: Added 6 new tests (3 service + 3 CLI) covering model validation, empty lists, URL verification, and JSON output

### Test Coverage
- test_list_channels_returns_channel_objects: validates Channel model_validate with displayName alias
- test_list_channels_empty: validates empty payload handling
- test_list_channels_uses_correct_url: validates team_id is included in Graph API URL
- test_channels_cli_command_smoke: validates CLI invocation with --team flag
- test_channels_cli_json_output: validates --json output formatting
- Plus 2 existing team tests still passing

### All Checks Passing
✓ ruff check src/ tests/ (0 issues)
✓ pyright src/ (0 errors)
✓ pytest tests/ -v (26 passed, +5 new channel tests)
✓ uv run ms-teams channels --help (exit 0, shows --team required)

### Inheritance from Previous Tasks
- Pydantic Field(alias="displayName") + model_config pattern from Task 3
- Service layer with _client.get() and model_validate() from Task 3
- CLI command structure with inline imports and TeamsError handling from Task 3
- Monkeypatch testing pattern with FakeGraphClient from Task 3

## [2026-05-18] Task 5: get-messages
- Added ChannelMessage, MessageAuthor, and MessageBody models with a before-validator that safely maps Graph `from.user.displayName` into an `author` field while preserving populate-by-name behavior.
- Kept message retrieval lazy end-to-end: GraphClient.paginate() yields raw items, ChannelService.get_messages() yields validated ChannelMessage objects, and presentation handles filtering/HTML cleanup.
- Introduced domain text helpers for HTML stripping and ISO datetime formatting, then reused them only in the message formatter to keep presentation concerns out of service/model layers.
- Extended CLI/tests using the existing teams/channels pattern, including smoke coverage for `messages`, URL construction with `since`, and evidence files for text/model/pagination behaviors.

## [2026-05-18] Task 7: unanswered + scan

### Implementation
- Added `find_unanswered()` with all 5 AND conditions faithfully ported from `_src.py:520-558`
- Added `scan_activity()` with exact algorithm from `_src.py:560-678`: date validation, stop_before=target-3d, channel iteration, root collection, reply fetching, thread inclusion logic
- Three new domain models: `ThreadActivity`, `ChannelActivity`, `ScanResult` (all with `model_config: ClassVar[ConfigDict]`)
- Two new formatters: `format_unanswered_table()` (mirrors messages table style), `format_scan_result()` (per-channel thread summaries)
- Two new CLI commands: `unanswered` (--team, --channel, --minutes) and `scan` (--team, --date, --pages, --top, --json)

### Key Decisions
1. **replyCount type safety**: `m.get("replyCount")` returns `object` from `dict[str, object]`. Used `isinstance(reply_count, int) and reply_count > 0` instead of `(m.get("replyCount") or 0) > 0` to satisfy pyright
2. **datetime.UTC alias**: Ruff UP017 requires `datetime.UTC` over `timezone.utc` in Python 3.13
3. **FakeGraphClient.paginate**: Added `stop_before: str | None = None` parameter to match real GraphClient signature
4. **ValueError for scan date**: CLI catches `ValueError` separately from `TeamsError` since date validation is business logic, not an API error
5. **Sequential API calls**: Kept scan_activity sequential (no asyncio/threading) matching `_src.py` behavior exactly

### Gotchas
- `paginate()` returns `Iterator` not `list` — need `list()` wrapper when collecting all results for dict comprehension
- String date comparison (`createdDateTime[:10] >= stop_before`) works correctly for ISO dates
- `.sisyphus/` is gitignored — evidence files exist on disk but not in git

### All Checks Passing
✓ ruff check src/ tests/ (0 issues)
✓ pyright src/ (0 errors, 0 warnings)
✓ pytest tests/ -v (51 passed — 10 new Task 7 tests)
✓ uv run ms-teams unanswered --help (exit 0)
✓ uv run ms-teams scan --help (exit 0)

## [2026-05-18] Task 8: parse-url + token

### Key Decisions
1. **URL Parser as Pure Function**: `parse_teams_url()` is a stateless, pure function with no side effects. Returns `TeamsUrlComponents` Pydantic model for type safety.
2. **Regex Patterns**: Used three fallback patterns (`/l/message/`, `/l/channel/`, `/l/team/`) to handle different Teams URL formats. Message pattern captures both channel and message IDs.
3. **CLI Argument Handling**: `parse-url` accepts optional URL argument; prompts interactively if TTY and URL not provided; errors if non-TTY and URL missing.
4. **Token Command**: Calls `AzGraphTokenProvider.renew()` to force refresh, then reads cache file directly to get expiry timestamp in ISO format.

### Patterns & Conventions
- **Lazy Imports**: All CLI commands import dependencies inside function body (not at module level) for faster startup.
- **Error Handling**: Use `typer.echo(str(exc), err=True)` + `raise typer.Exit(code=1)` for consistent error reporting.
- **Type Annotations**: All functions require full type hints; use `Annotated[...]` for CLI options/arguments.
- **Pydantic Models**: Always include `model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)` for consistency.

### Gotchas & Lessons
1. **Line Length**: Ruff enforces 100-char limit; split long f-strings across multiple lines with implicit concatenation.
2. **Unused Imports**: Removed unused `datetime`, `UTC` imports and unused `pytest` import to pass ruff checks.
3. **Type Narrowing**: Used `assert isinstance(url, str)` after conditional assignment to satisfy pyright's type checker.
4. **Binary Operators**: Prefer `x or default` over if-else blocks for simple fallbacks (SIM108 rule).

### Test Coverage
- 8 tests for URL parser covering: full message URLs, URL encoding, channel-only URLs, team URLs, no-match cases, query params, empty strings, return type validation.
- All 59 tests passing (51 existing + 8 new).


## [2026-05-18] Task 10: unread + chat-messages
- `consumptionhorizon` uses `or {}` pattern that triggers pyright "partially unknown" — use `conv.get(...)` without `or` then isinstance-check into cast
- Chat API `lastMessage.id` is a numeric string (unix-ms timestamp); compare as int
- `_as_payloads()` helper is reusable across all chat service methods
- `model_validate()` with `populate_by_name=True` + aliases handles the lowercase chat API field names (messagetype, composetime, imdisplayname)
- Evidence files go in `.sisyphus/evidence/` which is gitignored — don't try to `git add` them
- Test count reached 100 (≥99 required) — 29 in test_chats.py alone

## [2026-05-18] Task 11: send-message
- `ChatServiceClient.post(url, body)` returns `dict[str, object]` — use `.get()` for result fields
- `messagetype` detection: simple `"<" in message` check distinguishes HTML from plain text
- NO robot emoji prefix (🤖) — explicitly removed from original `_src.py` behavior per spec
- TTY detection pattern: `sys.stdin.isatty()` — if piped (non-TTY), skip confirmation (scripting-friendly)
- `--yes` flag provides explicit confirmation bypass independent of TTY state
- `resolve_chat_name()` wraps in `try/except Exception` with `# noqa: BLE001` — API errors shouldn't crash name resolution
- FakeChatClient needed `post()` method + `post_calls` tracker + `post_response` field for send tests
- 108 tests total (8 new), all passing

## [2026-05-18] Task 12: Polish
- Added a global Typer callback with `--verbose` / `-v` and a custom `TeamsTyperGroup` wrapper so CLI-level `KeyboardInterrupt` and uncaught `TeamsError` exit cleanly with user-facing stderr output.
- Moved the `if __name__ == "__main__": app()` guard to the very end of `presentation/cli.py` and exported the public package surface via `src/ms_teams_cli/__init__.py` while keeping loguru disabled by default at import time.
- Raised coverage by adding dedicated formatter tests plus CLI polish/integration tests for help output, empty-result behavior, token flows, parse-url prompting, send-message confirmation, and command-level error handling; final suite reached 87.12% coverage.
