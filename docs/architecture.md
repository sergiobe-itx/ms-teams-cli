# Architecture

ms-teams-cli follows **Hexagonal Architecture** (Ports & Adapters) with strict layer separation.

## Layer diagram

```
┌─────────────────────────────────────────────────────┐
│                   Presentation                      │
│  ┌──────────────┐            ┌──────────────┐       │
│  │   cli/       │            │   mcp/       │       │
│  │  (Typer)     │            │  (FastMCP)   │       │
│  └──────┬───────┘            └──────┬───────┘       │
│         │                           │               │
│         └─────────┬─────────────────┘               │
│                   │                                 │
│         ┌─────────▼─────────┐                       │
│         │  dependencies.py  │  ← Composition Root   │
│         └─────────┬─────────┘                       │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────┐
│                   │     Application                 │
│         ┌─────────▼─────────┐                       │
│         │    Use Cases      │                       │
│         │  (orchestration)  │                       │
│         └─────────┬─────────┘                       │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────┐
│                   │       Domain                    │
│         ┌─────────▼─────────┐                       │
│         │  Entities, Ports  │                       │
│         │  (interfaces)     │                       │
│         └───────────────────┘                       │
└─────────────────────────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────┐
│                   │    Infrastructure               │
│    ┌──────────────▼──────────────┐                  │
│    │  GraphClient, Repositories  │                  │
│    │  Auth Providers, TokenCache │                  │
│    └─────────────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

## Directory structure

```
src/ms_teams_cli/
├── __init__.py              # Public API re-exports
├── py.typed                 # PEP 561 marker
├── domain/
│   ├── entities.py          # Team, Channel, Chat, Message, CalendarEvent...
│   ├── exceptions.py        # TeamsError, AuthenticationError, APIError
│   ├── ports.py             # Repository & TokenProvider interfaces (Protocol)
│   └── services/            # Pure domain logic (text parsing, URL parsing)
├── application/
│   └── use_cases/           # One class per use case (single execute() method)
├── infrastructure/
│   ├── auth/                # Token provider (MSAL device-code flow)
│   └── graph/               # Microsoft Graph API client & repositories
└── presentation/
    ├── dependencies.py      # Composition root (wires the object graph)
    ├── cli/                 # Typer CLI (driving adapter)
    │   ├── _app.py          # App instance, callback, auth commands
    │   ├── channels.py      # Channel-related commands
    │   ├── chats.py         # Chat-related commands
    │   ├── calendar.py      # Calendar commands
    │   └── formatters.py    # Rich table + JSON output formatters
    └── mcp/                 # MCP server (driving adapter)
        ├── server.py        # FastMCP server with 12 tools
        └── config.py        # Send-message allowlist
```

## Design principles

### No DI framework

Dependencies are wired manually in `dependencies.py` via constructor injection. Each `get_*()` function constructs the full object graph for a use case.

### No async

The Microsoft Graph API calls are synchronous (httpx without async). This keeps the codebase simple and avoids async coloring.

### Ports as Protocols

Domain ports use `typing.Protocol` — infrastructure implements them without inheriting from abstract base classes. This allows structural subtyping.

### Use cases are thin

Each use case has a single `execute()` method that orchestrates one domain operation. Business rules live in domain services; I/O lives in infrastructure.

### Two driving adapters

Both `cli/` and `mcp/` are symmetric driving adapters that consume the same use cases through the same composition root. Neither knows about the other.

## Authentication flow

```
User request
    │
    ▼
MsalGraphTokenProvider (cached token → silent refresh → device-code login)
    │
    ▼
GraphClient (httpx) → Microsoft Graph API
```

## Testing strategy

- **Unit tests** — All use cases, domain services, repositories (httpx mocked via pytest-httpx)
- **No integration tests** — Graph API requires real auth; tested manually
- **Test isolation** — Each test builds its own object graph via fixtures
- **Coverage** — Measured via pytest-cov, configured in pyproject.toml
