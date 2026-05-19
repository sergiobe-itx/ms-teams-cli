# ms-teams-cli

> A Python CLI and MCP server for Microsoft Teams — read channels, chats, calendar events, and send
> messages via the Microsoft Graph API.

## 1. Overview

Two interfaces, one codebase:

- **`ms-teams`** — Terminal commands for humans (Rich-formatted tables, JSON output)
- **`ms-teams-mcp`** — 12 tools for AI agents (Claude, OpenCode, Cursor) via stdio

Built with Hexagonal Architecture, fully typed (pyright strict), and covered by 190+ tests.

### 1.1. Why This Exists

Teams has no usable CLI. The web app is slow, notifications are noisy, and there's no way to
script interactions. This tool gives developers:

- Quick terminal access to unread messages, channel activity, and calendar
- AI agent integration for automated workflows (async daily standups, message triage)
- A clean Python API that respects architectural boundaries

## 2. Quick Start

```bash
# Install
uv pip install ms-teams-cli

# Authenticate (one-time device-code flow)
ms-teams login

# Use
ms-teams chats              # List all chats
ms-teams unread             # Chats with unread messages
ms-teams calendar 2026-05-19 2026-05-19  # Today's meetings
ms-teams scan <team-id>     # Channel activity today
```

## 3. MCP Server (for AI Agents)

The MCP server exposes the same functionality as structured tools over stdio:

```json
{
  "mcpServers": {
    "ms-teams": {
      "command": "ms-teams-mcp"
    }
  }
}
```

Or from source:

```json
{
  "mcpServers": {
    "ms-teams": {
      "command": "uv",
      "args": ["--directory", "/path/to/ms-teams-cli", "run", "ms-teams-mcp"]
    }
  }
}
```

### 3.1. Available Tools

| Tool | Description |
|------|-------------|
| `teams_list_chats` | List chats (optionally filter by type) |
| `teams_list_unread` | List chats with unread messages |
| `teams_get_chat_messages` | Get messages from a chat |
| `teams_send_message` | Send a message to an allowlisted chat |
| `teams_resolve_chat_name` | Resolve a chat ID to its display name |
| `teams_list_teams` | List all joined teams |
| `teams_list_channels` | List channels in a team |
| `teams_get_channel_messages` | Get messages from a channel |
| `teams_get_thread` | Get a thread (parent + replies) |
| `teams_find_unanswered` | Find posts with no replies within N minutes |
| `teams_scan_activity` | Scan all channels for activity on a date |
| `teams_list_calendar_events` | List calendar events in a date range |

### 3.2. Send-Message Safety

The `teams_send_message` tool requires an explicit allowlist. Without it, all sends are blocked.
See [Usage → Send message allowlist](docs/usage.md#send-message-allowlist) for configuration.

## 4. CLI Commands

| Command | Description |
|---------|-------------|
| `login` | Authenticate via MSAL device-code flow |
| `logout` | Clear the token cache |
| `token` | Force token renewal and show status |
| `teams` | List all teams |
| `channels` | List channels in a team |
| `messages` | List messages in a channel |
| `replies` | Show a thread with all replies |
| `unanswered` | Find posts with no replies |
| `scan` | Scan team channels for activity on a date |
| `chats` | List chats |
| `unread` | List chats with unread messages |
| `chat-messages` | Show messages from a chat |
| `send-message` | Send a message to a chat |
| `calendar` | List calendar events in a date range |
| `parse-url` | Extract IDs from a Teams URL |
| `version` | Show version |

All commands support `--json` for machine-readable output.

## 5. High-Level Architecture

```
┌────────────────────────────────────────────────────┐
│  Presentation (driving adapters)                   │
│  ┌─────────────┐          ┌─────────────┐          │
│  │  CLI/Typer  │          │ MCP/FastMCP │          │
│  └──────┬──────┘          └──────┬──────┘          │
│         └────────┬───────────────┘                 │
│                  ▼                                 │
│         dependencies.py (composition root)         │
└──────────────────┬─────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────┐
│  Application (use cases — thin orchestrators)    │
└──────────────────┬───────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────┐
│ Domain (entities, ports, services — pure Python) │
└──────────────────┬───────────────────────────────┘
                   ▲ implements
┌──────────────────┴───────────────────────────────┐
│  Infrastructure (Graph API client, MSAL auth)    │
└──────────────────────────────────────────────────┘
```

## 6. Authentication

```bash
ms-teams login
```

Opens a browser-based MSAL device-code flow. Tokens are cached locally and refreshed
automatically on subsequent commands. No Azure CLI or service principal required.

## 7. Documentation

| Document | Contents |
|----------|----------|
| [Installation](docs/installation.md) | Prerequisites, install methods, auth setup, required permissions |
| [Usage](docs/usage.md) | CLI examples, MCP configuration, tool reference |
| [Architecture](docs/architecture.md) | Hexagonal design, layer responsibilities, design rationale |
| [Testing](docs/testing.md) | Test layers, mocking strategy, coverage approach |
| [Contributing](docs/contributing.md) | Dev workflow, golden rules, commit conventions |
| [Caveats & Future Work](docs/caveats.md) | Known limitations, technical debt, roadmap |

## 8. Tech Stack

| Concern | Tool |
|---------|------|
| Language | Python 3.13 |
| Package manager | uv |
| HTTP client | httpx |
| Auth | msal |
| CLI framework | Typer + Rich |
| MCP framework | FastMCP |
| Type checker | pyright (strict) |
| Linter/formatter | ruff |
| Testing | pytest + pytest-httpx + pytest-cov |

## License

[MIT](LICENSE)
