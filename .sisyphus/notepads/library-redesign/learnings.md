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
