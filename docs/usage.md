# Usage

## CLI

### Global options

```bash
ms-teams --verbose/-v  # Increase verbosity (repeatable: -vv, -vvv)
ms-teams --help        # Show help for any command
```

### Chats

```bash
# List all chats
ms-teams chats

# Filter by type (1:1, group, meeting, other)
ms-teams chats --chat-type group

# List chats with unread messages
ms-teams unread

# Read messages from a chat
ms-teams chat-messages <chat-id>
ms-teams chat-messages <chat-id> --top 50

# Send a message
ms-teams send-message <chat-id> "Hello from the CLI"
```

### Channels

```bash
# List teams
ms-teams teams

# List channels in a team
ms-teams channels <team-id>

# Read channel messages
ms-teams messages <team-id> <channel-id>
ms-teams messages <team-id> <channel-id> --since 2026-05-18

# Read a thread
ms-teams replies <team-id> <channel-id> <message-id>

# Find unanswered posts (no replies in last 120 minutes)
ms-teams unanswered <team-id> <channel-id>
ms-teams unanswered <team-id> <channel-id> --minutes 60

# Scan all channels in a team for activity on a date
ms-teams scan <team-id> --date 2026-05-19
```

### Calendar

```bash
# List events for today
ms-teams calendar 2026-05-19 2026-05-19

# List events for a range
ms-teams calendar 2026-05-19 2026-05-23
```

### Utilities

```bash
# Parse a Teams URL into structured IDs
ms-teams parse-url "https://teams.microsoft.com/l/message/..."

# Show version
ms-teams version
```

### Output format

All commands output Rich-formatted tables by default. Use `--json` for machine-readable JSON output:

```bash
ms-teams chats --json
ms-teams calendar 2026-05-19 2026-05-19 --json
```

---

## MCP Server

The MCP server exposes the same functionality as tools for AI agents.

### Setup

```bash
# Run directly (stdio transport)
ms-teams-mcp
```

### Client configuration

**OpenCode** (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "ms-teams": {
      "type": "local",
      "command": ["ms-teams-mcp"],
      "enabled": true
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ms-teams": {
      "command": "ms-teams-mcp"
    }
  }
}
```

### Send message allowlist

For safety, the `teams_send_message` tool requires an explicit allowlist. Without it, all sends are blocked.

Create `~/.config/ms-teams-cli/mcp.json`:

```json
{
  "allowed_chats": [
    "19:abc123@unq.gbl.spaces",
    "19:def456@unq.gbl.spaces"
  ]
}
```

To find chat IDs, use:

```bash
ms-teams chats --json | jq '.[].id'
```

### Tool reference

All tools return JSON. On error, they return `{"error": "..."}`.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `teams_list_chats` | `top?`, `chat_type?` | List chats |
| `teams_list_unread` | `chat_type?` | Chats with unread messages |
| `teams_get_chat_messages` | `chat_id`, `top?` | Messages from a chat |
| `teams_send_message` | `chat_id`, `message` | Send message (allowlisted only) |
| `teams_resolve_chat_name` | `chat_id` | Resolve chat display name |
| `teams_list_teams` | — | All joined teams |
| `teams_list_channels` | `team_id` | Channels in a team |
| `teams_get_channel_messages` | `team_id`, `channel_id`, `top?`, `pages?`, `since?` | Channel messages |
| `teams_get_thread` | `team_id`, `channel_id`, `message_id`, `top?` | Thread (parent + replies) |
| `teams_find_unanswered` | `team_id`, `channel_id`, `minutes?` | Unanswered posts |
| `teams_scan_activity` | `team_id`, `date`, `pages?`, `top?` | Scan channels for activity |
| `teams_list_calendar_events` | `start_date`, `end_date` | Calendar events (YYYY-MM-DD) |
