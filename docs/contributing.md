# Development Guidelines & Contributing

> Architecture boundaries, local workflow, and conventions for extending ms-teams-cli.

## 1. The Golden Rules

These boundaries maintain the integrity of the hexagonal architecture. Violating them will be
caught in code review:

1. **Domain imports nothing.** The `domain/` layer has zero imports from `infrastructure/`,
   `application/`, `presentation/`, or any external library (no httpx, no msal, no typer). Only
   stdlib + typing.
2. **Application depends only on domain.** Use cases import ports and entities — never concrete
   implementations.
3. **Infrastructure implements domain ports.** Adapters satisfy `typing.Protocol` interfaces via
   structural subtyping. No inheritance from abstract base classes.
4. **Presentation wires everything.** `dependencies.py` is the sole file that imports from all
   layers. CLI and MCP commands call factory functions — they never instantiate infrastructure
   directly.
5. **No DI frameworks.** Constructor injection only. The object graph is small enough to wire
   manually.
6. **No async.** Keep it synchronous. This is a single-user tool, not a multi-tenant server.
7. **No type suppression.** No `as any`, `# type: ignore` without a comment justifying it, or
   `@no_type_check`. Pyright strict must pass.

## 2. Local Developer Loop

### 2.1. Setup

```bash
git clone https://github.com/inditex/ms-teams-cli.git
cd ms-teams-cli
uv sync
```

This installs all dependencies (including dev tools) into a local `.venv`.

### 2.2. Quality Gates (run before every PR)

```bash
# Type checking (strict mode, zero errors required)
uv run pyright

# Lint (zero violations required)
uv run ruff check .

# Auto-fix lint issues + format
uv run ruff check --fix .
uv run ruff format .

# Tests (all must pass)
uv run pytest

# Tests with coverage report
uv run pytest --cov
```

**All checks must pass before merging.** The bar: 0 pyright errors, 0 ruff violations, all tests
green.

### 2.3. Verifying Entry Points

After any change to the presentation layer, verify both entry points still work:

```bash
ms-teams --help
ms-teams-mcp --help
```

## 3. Code Style

| Rule | Enforcement |
|------|-------------|
| Python 3.13 syntax (`type` statements, `\|` unions, f-strings) | pyright strict |
| Line length: 100 chars | ruff (`line-length = 100`) |
| Import sorting | ruff (isort rules) |
| No `Any` types without justification | pyright strict |
| Docstrings only where non-obvious | Code review |

## 4. Adding Features

### 4.1. Adding a New CLI Command

1. Create or extend a use case in `application/use_cases/`.
2. If new Graph API calls are needed, add methods to the appropriate repository in
   `infrastructure/graph/`.
3. Add the CLI command in the appropriate `presentation/cli/` module.
4. Wire the use case factory in `presentation/dependencies.py`.
5. Write tests covering:
   - The use case (mocked repository via `pytest-httpx`)
   - The CLI output (via `typer.testing.CliRunner`)

### 4.2. Adding a New MCP Tool

1. Add the tool function in `presentation/mcp/server.py` with `@mcp.tool()`.
2. Wire the use case getter in `dependencies.py` if new.
3. Return JSON via `json.dumps()` — always handle `TeamsError` gracefully.
4. Update the README MCP tool table.

### 4.3. Adding a New Graph API Endpoint

1. Define the domain entity in `domain/entities.py` (if new data shape).
2. Add the port method to the appropriate protocol in `domain/ports.py`.
3. Implement the method in the corresponding `infrastructure/graph/` repository.
4. Create a use case in `application/use_cases/`.
5. Expose via CLI and/or MCP as above.

## 5. Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): fix a bug
refactor(scope): code change that neither fixes nor adds
test(scope): add or update tests
docs(scope): documentation only
```

**Scopes:** `cli`, `mcp`, `domain`, `auth`, `graph`, `chat`, `calendar`, `presentation`

### 5.1. Commit Discipline

- One logical change per commit. Don't mix refactoring with feature work.
- If a refactor is needed to support a feature, commit the refactor first.
- Tests accompany the code they test in the same commit.

## 6. Testing Guidelines

- Every use case has its own test file.
- Use `pytest-httpx` for mocking Graph API responses.
- Tests are synchronous (no async fixtures needed).
- Monkeypatch `presentation.dependencies` for CLI/MCP integration tests.
- Test file location mirrors source: `tests/application/`, `tests/infrastructure/`,
  `tests/presentation/`.
- **Never delete a failing test to make CI pass.** Fix the code or fix the test.

For detailed testing strategy, see **[Testing](./testing.md)**.

## 7. Further Reading

- **[Architecture](./architecture.md)** — Layer responsibilities and design rationale.
- **[Testing](./testing.md)** — Test layers, mocking approach, and coverage.
- **[Caveats & Future Work](./caveats.md)** — Known limitations and planned improvements.
