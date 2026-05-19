# Installation & Usage Setup

> Prerequisites, installation methods, authentication, and required permissions.

## 1. Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip

## 2. Installation

### 2.1. From Artifactory (recommended)

```bash
uv pip install ms-teams-cli
```

Or with pip:

```bash
pip install ms-teams-cli
```

### 2.2. From Source

```bash
git clone https://github.com/inditex/ms-teams-cli.git
cd ms-teams-cli
uv sync
```

## 3. Verify Installation

```bash
ms-teams version
ms-teams --help
ms-teams-mcp --help
```

All three commands should produce output without errors.

## 4. Authentication

### 4.1. Initial Login

```bash
ms-teams login
```

This opens a browser-based MSAL device-code flow:

1. The CLI prints a URL and a one-time code.
2. You open the URL in a browser, enter the code, and sign in with your Microsoft account.
3. The token is cached at `~/.config/ms-teams-cli/msal_cache.json` and refreshed automatically.

### 4.2. Token Management

```bash
# Check token status and force renewal
ms-teams token

# Sign out (clear MSAL cache)
ms-teams logout
```

### 4.3. How Token Refresh Works

On every command invocation:

1. MSAL checks the local cache for a valid access token → uses it if found.
2. If expired, MSAL uses the refresh token to silently acquire a new access token.
3. If both are invalid, the command fails with `"Not logged in via MSAL. Run: ms-teams login"`.

You should rarely need to re-authenticate. Refresh tokens are long-lived (typically 90 days with
activity).

## 5. Required API Permissions

The following Microsoft Graph API scopes are requested during authentication:

| Scope | Purpose |
|-------|---------|
| `Chat.Read` | Read chats and messages |
| `Chat.ReadWrite` | Send messages |
| `ChannelMessage.Read.All` | Read channel messages |
| `Team.ReadBasic.All` | List joined teams |
| `Channel.ReadBasic.All` | List channels |
| `Calendars.Read` | Read calendar events |

These scopes are pre-authorized via the Microsoft Graph CLI public client. No admin consent is
required in most Microsoft 365 tenants.

## 6. Further Reading

- **[Usage](./usage.md)** — CLI commands, MCP setup, and tool reference.
- **[Architecture](./architecture.md)** — How the tool is structured internally.
