# ms-teams-cli

A Python CLI and MCP server for Microsoft Teams — read channels, chats, calendar events, and send messages via the Microsoft Graph API.

## Features

- **CLI** (`ms-teams`) — Typer-based terminal commands for channels, chats, calendar, and team management
- **MCP Server** (`ms-teams-mcp`) — 12 tools exposable to AI agents (Claude, OpenCode, Cursor, etc.) via stdio
- **Auth** — MSAL device-code flow with persistent token cache
- **Architecture** — Hexagonal (ports & adapters), fully typed (pyright strict), 200+ tests

## Quick Start

```bash
# Install from Artifactory
uv pip install ms-teams-cli

# Authenticate (one-time)
ms-teams login

# Use
ms-teams chats
ms-teams unread
ms-teams calendar 2026-05-19 2026-05-19
```

## MCP Server (for AI agents)

Add to your AI client config (Claude Desktop, OpenCode, Cursor, etc.):

```json
{
  "mcpServers": {
    "ms-teams": {
      "command": "ms-teams-mcp"
    }
  }
}
```

Or if running from source:

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

### Available MCP Tools

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

## CLI Commands

| Command | Description |
|---------|-------------|
| `login` | Authenticate via MSAL device-code flow |
| `logout` | Clear the token cache |
| `token` | Force token renewal and show expiry |
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

## Authentication

Run `ms-teams login` to authenticate via MSAL device-code flow. Tokens are cached at `~/.config/ms-teams-cli/` and refreshed automatically.

## Documentation

- [Installation](docs/installation.md) — Prerequisites, install methods, verification
- [Usage](docs/usage.md) — CLI and MCP usage guide with examples
- [Architecture](docs/architecture.md) — Hexagonal design, layers, and decisions
- [Contributing](docs/contributing.md) — Dev setup, testing, code style

## License

[MIT](LICENSE)