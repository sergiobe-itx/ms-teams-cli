# Architecture

> Hexagonal Architecture (Ports & Adapters) with strict layer separation, structural typing, and
> manual dependency injection.

## 1. Architectural Principles

### 1.1. Hexagonal Architecture (Why?)

The Microsoft Graph API is an external dependency that changes independently of our business logic.
By placing it behind domain-defined ports (interfaces), we achieve:

- **Testability** — All Graph API interactions are mocked via `pytest-httpx` without touching real
  endpoints.
- **Replaceability** — The auth strategy was swapped (chained → MSAL-only) without modifying a
  single use case or domain file.
- **Dual presentation** — CLI and MCP server share the same use cases through the same composition
  root, with zero awareness of each other.

### 1.2. Package by Layer (Not by Feature)

The domain is compact — Teams entities, Graph API ports, and text-processing services. A "package
by feature" approach would create unnecessary nesting for a single bounded context. Each layer has a
clear responsibility boundary:

```
Presentation  →  knows: Application, Infrastructure (via composition root)
Application   →  knows: Domain only
Domain        →  knows: nothing (pure Python, no framework imports)
Infrastructure→  knows: Domain (implements its ports)
```

### 1.3. Structural Typing (Protocols over ABCs)

Domain ports use `typing.Protocol` instead of abstract base classes. Infrastructure adapters satisfy
them implicitly — no inheritance required. This eliminates coupling between the domain definition
and its implementations: any object with a matching `get_token() → str` method satisfies
`GraphTokenProvider`.

## 2. Layer Breakdown

### 2.1. Domain (`domain/`)

The heart of the system. Contains zero imports from any other layer or external library.

- **Entities** (`entities.py`) — `Team`, `Channel`, `Chat`, `ChannelMessage`, `ChatMessage`,
  `CalendarEvent`, `ScanResult`. Pure dataclasses representing Graph API concepts.
- **Ports** (`ports.py`) — `GraphTokenProvider`, `ChannelRepository`, `ChatRepository`,
  `CalendarRepository`. Protocol classes defining what the infrastructure must provide.
- **Services** (`services/`) — Stateless business logic. `TextService` strips HTML and normalizes
  message content. `UrlParser` extracts structured IDs from Teams deep-link URLs.
- **Exceptions** (`exceptions.py`) — `TeamsError` (root), `AuthenticationError`,
  `APIError`. Layered hierarchy for precise error handling at each boundary.

### 2.2. Application (`application/use_cases/`)

Thin orchestrators — one class per use case, each with a single `execute()` method. They receive
a repository (port) via constructor injection and delegate all I/O through it.

- **No business logic here.** If a rule doesn't involve I/O coordination, it belongs in a domain
  service.
- **No framework imports.** Use cases know nothing about HTTP, CLI, or MCP.

Examples: `ListChatsUseCase`, `GetThreadUseCase`, `ScanActivityUseCase`,
`ListCalendarEventsUseCase`.

### 2.3. Infrastructure (`infrastructure/`)

Concrete implementations of domain ports. The only layer permitted to import external libraries
(httpx, msal).

- **`auth/`** — `MsalGraphTokenProvider` acquires Graph API tokens via MSAL device-code flow with
  persistent cache (`~/.config/ms-teams-cli/`). Implements `GraphTokenProvider` protocol.
- **`graph/`** — `GraphClient` (httpx-based HTTP client with automatic token injection and retry),
  `GraphChannelRepository`, `GraphChatRepository`, `GraphCalendarRepository`.

### 2.4. Presentation (`presentation/`)

Two symmetric **driving adapters** that consume the same use cases:

| Adapter | Technology | Entry Point | Role |
|---------|-----------|-------------|------|
| `cli/` | Typer | `ms-teams` | Terminal interface for humans |
| `mcp/` | FastMCP | `ms-teams-mcp` | Tool interface for AI agents |

Both delegate to the **composition root** (`dependencies.py`), which is the single file that knows
all layers and wires the full object graph.

## 3. Dependency Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation                         │
│  ┌──────────────┐              ┌──────────────┐         │
│  │   CLI/Typer  │              │  MCP/FastMCP │         │
│  └──────┬───────┘              └──────┬───────┘         │
│         └──────────┬──────────────────┘                 │
│                    │                                    │
│          ┌─────────▼─────────┐                          │
│          │  dependencies.py  │  ← sole wiring point     │
│          └─────────┬─────────┘                          │
└────────────────────┼────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────┐
│                    │       Application                  │
│          ┌─────────▼─────────┐                          │
│          │    Use Cases      │  ← one per operation     │
│          └─────────┬─────────┘                          │
└────────────────────┼────────────────────────────────────┘
                     │ depends on
┌────────────────────┼────────────────────────────────────┐
│                    │         Domain                     │
│          ┌─────────▼─────────┐                          │
│          │ Entities + Ports  │  ← pure Python           │
│          │ Services          │                          │
│          └───────────────────┘                          │
└────────────────────┬────────────────────────────────────┘
                     │ implemented by
┌────────────────────┼────────────────────────────────────┐
│                    │      Infrastructure                │
│     ┌──────────────▼──────────────────┐                 │
│     │  GraphClient + Repositories     │                 │
│     │  MsalGraphTokenProvider         │                 │
│     └─────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## 4. Directory Structure

```
src/ms_teams_cli/
├── __init__.py              # Public API re-exports
├── py.typed                 # PEP 561 marker
├── domain/
│   ├── entities.py          # Team, Channel, Chat, Message, CalendarEvent
│   ├── exceptions.py        # TeamsError, AuthenticationError, APIError
│   ├── ports.py             # Protocol interfaces (repositories, token provider)
│   └── services/            # Pure domain logic (text, URL parsing)
├── application/
│   └── use_cases/           # One class per use case (single execute())
├── infrastructure/
│   ├── auth/                # MSAL token provider + cache
│   └── graph/               # httpx client + Graph API repositories
└── presentation/
    ├── dependencies.py      # Composition root
    ├── cli/                 # Typer CLI (driving adapter)
    │   ├── _app.py          # App instance, callback, auth commands
    │   ├── channels.py      # Channel commands
    │   ├── chats.py         # Chat commands
    │   ├── calendar.py      # Calendar commands
    │   └── formatters.py    # Rich table + JSON output
    └── mcp/                 # MCP server (driving adapter)
        ├── server.py        # FastMCP server with 12 tools
        └── config.py        # Send-message allowlist
```

## 5. Key Design Decisions

### 5.1. No DI Framework

Dependencies are wired manually in `dependencies.py` via constructor injection. Each `get_*()`
function constructs the complete object graph for one use case.

- **Rationale:** The object graph is small (~15 nodes). A DI container adds complexity without
  meaningful benefit at this scale.
- **Trade-off:** Adding a new use case requires one new factory function. This is acceptable for a
  project of this size.

### 5.2. No Async

All Microsoft Graph API calls use synchronous httpx. The CLI runs sequentially; the MCP server
handles one tool call at a time via stdio.

- **Rationale:** Async provides no throughput benefit for a single-user CLI tool. It adds
  complexity (colored functions, event loop management) without measurable gain.
- **Trade-off:** If this were a multi-tenant web service, async would be required. For a personal
  CLI/MCP tool, synchronous is strictly simpler.

### 5.3. Two Driving Adapters (CLI + MCP)

Both adapters are peers — neither depends on the other. They share the same composition root and
use cases but have entirely different presentation concerns.

- **Rationale:** AI agents need structured JSON tool responses. Humans need Rich-formatted tables.
  Forcing both through a single interface would compromise both experiences.
- **Trade-off:** Some output logic is duplicated (e.g., error formatting). The shared use case
  layer prevents any business logic duplication.

### 5.4. `_app.py` Underscore Prefix

The CLI app module is named `_app.py` instead of `app.py`.

- **Rationale:** Python resolves `from cli import app` as the submodule `cli/app.py` before the
  attribute `cli.__init__.app`. The underscore prevents this name collision while keeping the public
  API clean (`from ms_teams_cli.presentation.cli import app`).

### 5.5. MSAL-Only Authentication

A single `MsalGraphTokenProvider` handles all token acquisition (silent cache → refresh →
interactive device-code).

- **Rationale:** Azure CLI tokens (`az account get-access-token`) lack the required Graph API
  scopes in our tenant. A chained fallback added complexity for a path that never worked.
- **Trade-off:** Users must run `ms-teams login` once. There is no "zero-setup" path for developers
  already authenticated via `az`.

## 6. Authentication Flow

```
ms-teams <command>
       │
       ▼
MsalGraphTokenProvider
       │
       ├── 1. Check MSAL token cache (~/.config/ms-teams-cli/msal_cache.json)
       │      └── Valid token? → return immediately
       │
       ├── 2. Attempt silent refresh (MSAL refresh token)
       │      └── Success? → update cache, return token
       │
       └── 3. Fail with AuthenticationError
              └── User runs: ms-teams login (device-code flow)
```

## 7. Further Reading

- **[Testing Strategy](./testing.md)** — Test layers, mocking approach, and coverage mechanics.
- **[Contributing](./contributing.md)** — Development workflow and architectural boundaries.
- **[Caveats & Future Work](./caveats.md)** — Known limitations and roadmap.
