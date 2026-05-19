# Caveats & Future Work

> Accepted technical debt, known limitations, and planned improvements.

## 1. Accepted Limitations

### 1.1. No Real-Time Notifications

The tool polls the Graph API on demand — it does not subscribe to real-time change notifications
(webhooks). You see what existed at the time of the request, not a live feed.

- **Rationale:** Change notifications require a publicly reachable HTTPS endpoint or a long-lived
  WebSocket connection. Neither fits a local CLI tool running on a developer's laptop.
- **Impact:** "Unread" state may be slightly stale. Running `ms-teams unread` twice in quick
  succession always fetches fresh data.

### 1.2. Single-User, Single-Tenant

The tool authenticates as the current user against one Azure AD tenant. There is no multi-account
switcher or service principal mode.

- **Rationale:** This is a personal productivity tool for Inditex developers, not a multi-tenant
  SaaS application.
- **Impact:** If you need to access Teams data across multiple tenants, you'd need separate
  installs with separate token caches.

### 1.3. Borrowed Client ID

The MSAL authentication uses Microsoft's pre-authorized Graph CLI client ID
(`14d82eec-204b-4c2f-b7e8-296a70dab67e`) rather than a custom app registration.

- **Rationale:** Avoids the overhead of creating and maintaining an Azure AD app registration.
  This client ID is well-known and pre-consented in most Microsoft 365 tenants.
- **Trade-off:** We depend on Microsoft keeping this app active. If it's deprecated or
  tenant-blocked, we'd need to register our own app.

### 1.4. No Pagination for Large Result Sets

Most commands use a fixed `top` parameter (default: 20-50 items). There is no automatic
"fetch all pages" loop.

- **Rationale:** The Graph API paginates via `@odata.nextLink`. Implementing transparent
  auto-pagination adds complexity and risks unbounded API calls for large teams.
- **Impact:** Power users with hundreds of chats or channels may need to increase `--top` or call
  repeatedly. The MCP tools accept `pages` parameters for controlled multi-page fetches.

### 1.5. Send-Message Allowlist (MCP Only)

The MCP `teams_send_message` tool requires an explicit allowlist of chat IDs in
`~/.config/ms-teams-cli/mcp.json`. Without it, all sends are blocked.

- **Rationale:** AI agents should not have unrestricted ability to send messages to any chat. The
  allowlist is a deliberate safety guardrail that requires human intent to configure.
- **Trade-off:** Initial setup friction. Users must look up chat IDs and add them manually.

## 2. Technical Debt

### 2.1. No Retry/Backoff on Graph API Errors

The `GraphClient` does not implement exponential backoff on 429 (rate limit) or 5xx responses.

- **Impact:** Burst usage (e.g., scanning many channels rapidly) may hit rate limits without
  automatic recovery.
- **Fix:** Add a retry decorator with exponential backoff and jitter to `GraphClient._request()`.

### 2.2. Token Cache Race Condition

If two processes (e.g., CLI and MCP server) run simultaneously, both may attempt to refresh the
MSAL token and write to the same cache file. MSAL's `SerializableTokenCache` is not designed for
multi-process access.

- **Impact:** Rare in practice (stdio MCP blocks on one call at a time), but theoretically
  possible. Worst case: one process gets a stale token and retries.
- **Fix:** File-level locking (`fcntl.flock`) on the MSAL cache path.

### 2.3. No Structured Logging

The CLI uses `loguru` for debug output (`--verbose`), but there is no structured JSON logging mode
for production observability.

- **Impact:** Fine for a developer tool. Would be inadequate if this became a server-side service.
- **Fix:** Add a `--log-format json` flag or environment variable.

## 3. Future Work

### 3.1. Channel Message Sending

Currently, `send-message` only supports chat messages. Channel message posting (via
`POST /teams/{id}/channels/{id}/messages`) is not implemented.

### 3.2. Message Search

The Graph API supports `$search` on messages. A `ms-teams search "keyword"` command would be
useful for finding conversations across chats and channels.

### 3.3. Presence & Status

Exposing user presence (`Available`, `Busy`, `Away`) via the `/users/{id}/presence` endpoint would
enable presence-aware automation (e.g., "don't send message if user is in DND").

### 3.4. Custom App Registration

Register a dedicated Azure AD app with precisely scoped permissions, rather than borrowing
Microsoft's Graph CLI client ID. This would give us control over consent and token lifetime.

### 3.5. CI/CD Pipeline

Set up GitHub Actions to:
- Run ruff + pyright + pytest on every PR
- Publish to internal Artifactory on merge to main
- Generate changelog from conventional commits

## 4. Further Reading

- **[Architecture](./architecture.md)** — Design decisions that led to these trade-offs.
- **[Testing](./testing.md)** — How we maintain confidence despite the above limitations.
