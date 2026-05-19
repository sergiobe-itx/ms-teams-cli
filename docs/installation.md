# Installation

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Install from Artifactory

```bash
uv pip install ms-teams-cli
```

Or with pip:

```bash
pip install ms-teams-cli
```

## Install from source

```bash
git clone https://github.com/inditex/ms-teams-cli.git
cd ms-teams-cli
uv sync
```

## Verify installation

```bash
ms-teams version
ms-teams --help
```

## Authentication setup

```bash
ms-teams login
```

This opens a browser-based device-code flow. Once authenticated, the token is cached at `~/.config/ms-teams-cli/token_cache.json` and refreshed automatically.

### Token management

```bash
# Check token status and force renewal
ms-teams token

# Sign out (clear MSAL cache)
ms-teams logout
```

## Required API permissions

The Microsoft Graph API scopes used:

- `Chat.Read` — Read chats and messages
- `Chat.ReadWrite` — Send messages
- `ChannelMessage.Read.All` — Read channel messages
- `Team.ReadBasic.All` — List teams
- `Channel.ReadBasic.All` — List channels
- `Calendars.Read` — Read calendar events
