# Contributing

## Development setup

```bash
git clone https://github.com/inditex/ms-teams-cli.git
cd ms-teams-cli
uv sync
```

This installs all dependencies (including dev tools) into a local `.venv`.

## Running checks

```bash
# Type checking (strict mode)
uv run pyright

# Linting
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .

# Format
uv run ruff format .

# Tests
uv run pytest

# Tests with coverage
uv run pytest --cov
```

All checks must pass before merging. Target: 0 pyright errors, 0 ruff violations, all tests green.

## Code style

- **Python 3.13** — Use modern syntax (`type` statements, `|` unions, etc.)
- **ruff** — Linter and formatter (configured in `pyproject.toml`)
- **pyright strict** — No `Any` types, no `# type: ignore` without justification
- **Line length** — 100 characters

## Architecture rules

1. **Domain has no imports from other layers** — Entities and ports are pure Python
2. **Application depends only on domain** — Use cases import ports, not implementations
3. **Infrastructure implements domain ports** — Via `typing.Protocol` (structural subtyping)
4. **Presentation wires everything** — `dependencies.py` is the only place that knows all layers
5. **No DI frameworks** — Constructor injection only
6. **No async** — Keep it simple

## Adding a new command

1. Create or extend a use case in `application/use_cases/`
2. If new Graph API calls are needed, add to the appropriate repository in `infrastructure/graph/`
3. Add the CLI command in the appropriate `presentation/cli/` file
4. Add the MCP tool in `presentation/mcp/server.py`
5. Wire the use case in `presentation/dependencies.py`
6. Write tests covering the use case and CLI output

## Adding a new MCP tool

1. Add the tool function in `presentation/mcp/server.py` with `@mcp.tool()`
2. Wire the use case getter in `presentation/dependencies.py` if new
3. Return JSON via `json.dumps()` — always handle `TeamsError`
4. Update README tool table

## Commit conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): fix a bug
refactor(scope): code change that neither fixes nor adds
test(scope): add or update tests
docs(scope): documentation only
```

Scopes: `cli`, `mcp`, `domain`, `auth`, `graph`, `chat`, `calendar`, `presentation`

## Testing guidelines

- Every use case has its own test file
- Use `pytest-httpx` for mocking Graph API responses
- Tests are synchronous (no async fixtures)
- Monkeypatch `presentation.dependencies` for CLI/MCP integration tests
- Test file location mirrors source: `tests/application/use_cases/`, `tests/infrastructure/`, `tests/presentation/`
