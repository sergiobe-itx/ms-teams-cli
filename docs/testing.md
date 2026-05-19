# Testing Strategy

> Layered testing approach with fast feedback, full isolation, and zero reliance on real Microsoft
> Graph API credentials.

## 1. Test Layers

### 1.1. Unit Tests (Domain + Application)

Validate pure business logic and use case orchestration in complete isolation.

- **Domain services** — `TextService` HTML stripping, `UrlParser` extraction logic. No mocks
  needed; these are pure functions.
- **Use cases** — Each use case is tested with a mocked repository. The mock returns predefined
  domain entities; the test asserts the use case produces the correct output.
- **Execution:** Deterministic, sub-second, no I/O.

### 1.2. Infrastructure Tests

Validate that infrastructure adapters correctly translate between the Graph API wire format and
domain entities.

- **Graph repositories** — Mocked at the HTTP level via `pytest-httpx`. Real JSON response
  payloads (captured from the Graph API) are fed to the repository; the test asserts correct
  entity mapping.
- **Auth providers** — MSAL library interactions are mocked to test token cache behavior, renewal
  logic, and error paths without real Azure AD calls.
- **Token cache** — File-system operations tested against `tmp_path` fixtures. Covers save/load,
  expiry detection, and margin handling.

### 1.3. Presentation Tests (CLI + MCP)

Validate the full path from user input to formatted output, with infrastructure mocked at the
composition root boundary.

- **CLI** — `typer.testing.CliRunner` invokes commands. Dependencies are monkeypatched to return
  fake data. Tests assert exit codes, stdout content, and stderr error messages.
- **MCP** — Tool functions are called directly with mocked use cases. Tests assert JSON output
  structure.

## 2. What We Mock (and Why)

| Boundary | Mock Technique | Rationale |
|----------|---------------|-----------|
| Microsoft Graph HTTP | `pytest-httpx` | No real credentials in CI; deterministic responses |
| MSAL library | `monkeypatch` on provider classes | Device-code flow requires browser interaction |
| File system (token cache) | `tmp_path` fixture | Isolation between tests; no ~/.config pollution |
| Composition root | `monkeypatch` on `dependencies.py` | CLI tests don't need real Graph calls |

## 3. What We Don't Mock

- **Domain services** — Pure functions, no need to mock. Test the real thing.
- **Entity construction** — Tests build real domain entities to validate data flow.
- **Typer CLI framework** — `CliRunner` exercises the actual Typer app instance.

## 4. Running Tests

```bash
# Full suite
uv run pytest

# With coverage
uv run pytest --cov

# Verbose output
uv run pytest -v

# Specific layer
uv run pytest tests/domain/
uv run pytest tests/application/
uv run pytest tests/infrastructure/
uv run pytest tests/presentation/

# Single test
uv run pytest tests/presentation/test_cli.py::test_token_command_success
```

## 5. Test Organization

Test file structure mirrors the source layout:

```
tests/
├── domain/
│   └── services/           # TextService, UrlParser tests
├── application/
│   └── use_cases/          # One test file per use case
├── infrastructure/
│   ├── auth/               # Token cache, MSAL provider tests
│   └── graph/              # Repository tests (httpx mocked)
└── presentation/
    ├── test_cli.py         # CLI command tests (all commands)
    ├── test_formatters.py  # Output formatting tests
    └── test_login_logout.py # Auth command tests
```

## 6. Design Decisions

### 6.1. No Integration Tests Against Real Graph API

- **Rationale:** The Graph API requires real Azure AD credentials and a real Teams tenant. Running
  these in CI is impractical and flaky. Manual testing against the real API is performed during
  development.
- **Trade-off:** We rely on `pytest-httpx` with realistic payloads. If Microsoft changes the API
  response shape, tests won't catch it until manual testing reveals it.

### 6.2. No Async Test Fixtures

- **Rationale:** The application is fully synchronous. Adding `pytest-asyncio` would add complexity
  for zero benefit.

### 6.3. Monkeypatch over Dependency Injection in Tests

- **Rationale:** CLI tests need to patch at the import boundary because Typer commands resolve
  dependencies at call time (lazy imports inside functions). Monkeypatch is idiomatic pytest for
  this pattern.

## 7. Coverage

Coverage is measured via `pytest-cov` and configured in `pyproject.toml`. The target is high
coverage on domain and application layers (business logic), with pragmatic coverage on presentation
(enough to catch regressions in command wiring and output formatting).

## 8. Further Reading

- **[Architecture](./architecture.md)** — Layer responsibilities and why the test boundaries exist
  where they do.
- **[Contributing](./contributing.md)** — How to write tests when adding features.
